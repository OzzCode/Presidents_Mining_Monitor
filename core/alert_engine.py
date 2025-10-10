"""Alert detection and evaluation engine for miner monitoring."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from sqlalchemy import func, and_, or_
from core.db import SessionLocal, Alert, AlertRule, Metric, Miner
from config import TEMP_THRESHOLD, HASHRATE_DROP_THRESHOLD, ALERT_COOLDOWN_MINUTES

logger = logging.getLogger(__name__)


class AlertEngine:
    """Evaluates alert rules against current miner metrics."""

    def __init__(self):
        self.session = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def check_all_miners(self) -> List[Alert]:
        """
        Check all active miners against all enabled alert rules.
        Returns list of new alerts created.
        """
        new_alerts = []

        try:
            # Get all enabled rules
            rules = self.session.query(AlertRule).filter(AlertRule.enabled == True).all()

            if not rules:
                logger.debug("No enabled alert rules")
                return new_alerts

            # Get latest metric per miner
            latest_subq = (
                self.session.query(
                    Metric.miner_ip.label('ip'),
                    func.max(Metric.timestamp).label('last_ts')
                ).group_by(Metric.miner_ip).subquery()
            )

            metrics = (
                self.session.query(Metric)
                .join(latest_subq, and_(
                    Metric.miner_ip == latest_subq.c.ip,
                    Metric.timestamp == latest_subq.c.last_ts
                ))
                .all()
            )

            # Get miner metadata
            miner_ips = [m.miner_ip for m in metrics]
            miners_dict = {}
            if miner_ips:
                miners = self.session.query(Miner).filter(Miner.miner_ip.in_(miner_ips)).all()
                miners_dict = {m.miner_ip: m for m in miners}

            # Evaluate each rule against each miner
            for rule in rules:
                for metric in metrics:
                    miner = miners_dict.get(metric.miner_ip)

                    # Check if rule applies to this miner
                    if not self._rule_applies_to_miner(rule, metric.miner_ip, miner):
                        continue

                    # Check if already alerted recently (cooldown)
                    if self._in_cooldown(rule, metric.miner_ip):
                        continue

                    # Evaluate rule
                    alert = self._evaluate_rule(rule, metric, miner)
                    if alert:
                        new_alerts.append(alert)
                        logger.info(f"Alert triggered: {alert.message} for {alert.miner_ip}")

            # Auto-resolve alerts for miners that recovered
            self._auto_resolve_alerts(metrics)

        except Exception as e:
            logger.exception("Error checking alerts", exc_info=e)

        return new_alerts

    def _rule_applies_to_miner(self, rule: AlertRule, ip: str, miner: Optional[Miner]) -> bool:
        """Check if a rule applies to a specific miner."""
        # Specific IP filter
        if rule.miner_ip and rule.miner_ip != ip:
            return False

        # Model filter
        if rule.model_filter and miner and miner.model:
            if rule.model_filter.lower() not in miner.model.lower():
                return False

        # Tags filter (if implemented)
        if rule.tags_filter and miner and miner.tags:
            # Simple tag matching - can be enhanced
            required_tags = rule.tags_filter if isinstance(rule.tags_filter, list) else []
            miner_tags = miner.tags if isinstance(miner.tags, list) else []
            if not any(tag in miner_tags for tag in required_tags):
                return False

        return True

    def _in_cooldown(self, rule: AlertRule, ip: str) -> bool:
        """Check if an alert for this rule/miner is in cooldown period."""
        cooldown_minutes = rule.cooldown_minutes or ALERT_COOLDOWN_MINUTES
        cutoff = datetime.utcnow() - timedelta(minutes=cooldown_minutes)

        recent_alert = (
            self.session.query(Alert)
            .filter(
                Alert.rule_id == rule.id,
                Alert.miner_ip == ip,
                Alert.created_at >= cutoff,
                Alert.status.in_(['active', 'acknowledged'])
            )
            .first()
        )

        return recent_alert is not None

    def _evaluate_rule(self, rule: AlertRule, metric: Metric, miner: Optional[Miner]) -> Optional[Alert]:
        """Evaluate a single rule against a metric."""
        try:
            thresholds = rule.thresholds or {}

            if rule.rule_type == 'offline':
                return self._check_offline(rule, metric, thresholds)
            elif rule.rule_type == 'temp':
                return self._check_temperature(rule, metric, thresholds)
            elif rule.rule_type == 'hashrate':
                return self._check_hashrate(rule, metric, miner, thresholds)
            elif rule.rule_type == 'fan':
                return self._check_fan(rule, metric, thresholds)
            elif rule.rule_type == 'power':
                return self._check_power(rule, metric, miner, thresholds)

        except Exception as e:
            logger.exception(f"Error evaluating rule {rule.id}", exc_info=e)

        return None

    def _check_offline(self, rule: AlertRule, metric: Metric, thresholds: Dict) -> Optional[Alert]:
        """Check if miner is offline/stale."""
        max_age_minutes = thresholds.get('max_age_minutes', 10)
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)

        # Ensure metric timestamp is timezone-aware
        metric_ts = metric.timestamp
        if metric_ts.tzinfo is None:
            metric_ts = metric_ts.replace(tzinfo=timezone.utc)

        cutoff_aware = cutoff.replace(tzinfo=timezone.utc)

        if metric_ts < cutoff_aware:
            age_minutes = (datetime.now(timezone.utc) - metric_ts).total_seconds() / 60
            return self._create_alert(
                rule=rule,
                miner_ip=metric.miner_ip,
                alert_type='offline',
                message=f"Miner offline for {age_minutes:.1f} minutes",
                details={'age_minutes': age_minutes, 'last_seen': metric_ts.isoformat()}
            )

        return None

    def _check_temperature(self, rule: AlertRule, metric: Metric, thresholds: Dict) -> Optional[Alert]:
        """Check if temperature exceeds threshold."""
        max_temp = thresholds.get('temp_c', TEMP_THRESHOLD)

        if metric.avg_temp_c and metric.avg_temp_c > max_temp:
            return self._create_alert(
                rule=rule,
                miner_ip=metric.miner_ip,
                alert_type='temp',
                message=f"Temperature {metric.avg_temp_c:.1f}°C exceeds threshold {max_temp}°C",
                details={'current_temp': metric.avg_temp_c, 'threshold': max_temp}
            )

        return None

    def _check_hashrate(self, rule: AlertRule, metric: Metric, miner: Optional[Miner],
                        thresholds: Dict) -> Optional[Alert]:
        """Check if hashrate dropped significantly."""
        if not metric.hashrate_ths:
            return None

        # Get baseline from miner metadata or threshold
        baseline_ths = None
        if miner and miner.nominal_ths:
            baseline_ths = miner.nominal_ths
        elif 'baseline_ths' in thresholds:
            baseline_ths = thresholds['baseline_ths']

        if not baseline_ths:
            # Try to calculate rolling average from recent metrics
            baseline_ths = self._get_rolling_average_hashrate(metric.miner_ip)

        if baseline_ths:
            drop_threshold = thresholds.get('drop_threshold', HASHRATE_DROP_THRESHOLD)
            min_expected = baseline_ths * drop_threshold

            if metric.hashrate_ths < min_expected:
                drop_pct = ((baseline_ths - metric.hashrate_ths) / baseline_ths) * 100
                return self._create_alert(
                    rule=rule,
                    miner_ip=metric.miner_ip,
                    alert_type='hashrate',
                    message=f"Hashrate {metric.hashrate_ths:.1f} TH/s is {drop_pct:.1f}% below baseline {baseline_ths:.1f} TH/s",
                    details={
                        'current_hashrate': metric.hashrate_ths,
                        'baseline_hashrate': baseline_ths,
                        'drop_percentage': drop_pct
                    }
                )

        return None

    def _check_fan(self, rule: AlertRule, metric: Metric, thresholds: Dict) -> Optional[Alert]:
        """Check if fan speed is abnormal."""
        if not metric.avg_fan_rpm:
            return None

        min_rpm = thresholds.get('min_rpm', 2000)
        max_rpm = thresholds.get('max_rpm', 6500)

        if metric.avg_fan_rpm < min_rpm:
            return self._create_alert(
                rule=rule,
                miner_ip=metric.miner_ip,
                alert_type='fan',
                message=f"Fan speed {metric.avg_fan_rpm:.0f} RPM below minimum {min_rpm} RPM",
                details={'current_rpm': metric.avg_fan_rpm, 'min_rpm': min_rpm}
            )
        elif metric.avg_fan_rpm > max_rpm:
            return self._create_alert(
                rule=rule,
                miner_ip=metric.miner_ip,
                alert_type='fan',
                message=f"Fan speed {metric.avg_fan_rpm:.0f} RPM exceeds maximum {max_rpm} RPM",
                details={'current_rpm': metric.avg_fan_rpm, 'max_rpm': max_rpm}
            )

        return None

    def _check_power(self, rule: AlertRule, metric: Metric, miner: Optional[Miner],
                     thresholds: Dict) -> Optional[Alert]:
        """Check if power consumption is abnormal."""
        if not metric.power_w:
            return None

        # Check against cap if set
        if miner and miner.power_cap_w:
            if metric.power_w > miner.power_cap_w * 1.05:  # 5% tolerance
                return self._create_alert(
                    rule=rule,
                    miner_ip=metric.miner_ip,
                    alert_type='power',
                    message=f"Power {metric.power_w:.0f}W exceeds cap {miner.power_cap_w:.0f}W",
                    details={'current_power': metric.power_w, 'power_cap': miner.power_cap_w}
                )

        # Check against thresholds
        max_power = thresholds.get('max_power_w')
        min_power = thresholds.get('min_power_w')

        if max_power and metric.power_w > max_power:
            return self._create_alert(
                rule=rule,
                miner_ip=metric.miner_ip,
                alert_type='power',
                message=f"Power {metric.power_w:.0f}W exceeds threshold {max_power}W",
                details={'current_power': metric.power_w, 'max_power': max_power}
            )

        if min_power and metric.power_w < min_power:
            return self._create_alert(
                rule=rule,
                miner_ip=metric.miner_ip,
                alert_type='power',
                message=f"Power {metric.power_w:.0f}W below threshold {min_power}W",
                details={'current_power': metric.power_w, 'min_power': min_power}
            )

        return None

    def _get_rolling_average_hashrate(self, ip: str, samples: int = 10) -> Optional[float]:
        """Calculate rolling average hashrate for baseline."""
        recent = (
            self.session.query(Metric.hashrate_ths)
            .filter(Metric.miner_ip == ip, Metric.hashrate_ths.isnot(None))
            .order_by(Metric.timestamp.desc())
            .limit(samples)
            .all()
        )

        if not recent:
            return None

        valid_rates = [r[0] for r in recent if r[0] and r[0] > 0]
        if not valid_rates:
            return None

        return sum(valid_rates) / len(valid_rates)

    def _create_alert(self, rule: AlertRule, miner_ip: str, alert_type: str,
                      message: str, details: Dict[str, Any]) -> Alert:
        """Create and persist a new alert."""
        alert = Alert(
            rule_id=rule.id,
            miner_ip=miner_ip,
            alert_type=alert_type,
            severity=rule.severity,
            message=message,
            details=details,
            status='active'
        )

        self.session.add(alert)
        self.session.commit()

        return alert

    def _auto_resolve_alerts(self, current_metrics: List[Metric]) -> None:
        """Auto-resolve alerts for miners that have recovered."""
        # Get all active alerts
        active_alerts = (
            self.session.query(Alert)
            .filter(Alert.status == 'active')
            .all()
        )

        # Build lookup of current states
        current_state = {}
        for metric in current_metrics:
            current_state[metric.miner_ip] = metric

        for alert in active_alerts:
            metric = current_state.get(alert.miner_ip)
            if not metric:
                continue

            should_resolve = False

            # Check if condition cleared
            if alert.alert_type == 'temp':
                threshold = (alert.details or {}).get('threshold', TEMP_THRESHOLD)
                if metric.avg_temp_c and metric.avg_temp_c <= threshold * 0.95:  # 5% hysteresis
                    should_resolve = True

            elif alert.alert_type == 'offline':
                # If we have recent data, miner is back online
                age = (datetime.utcnow() - metric.timestamp).total_seconds() / 60
                if age < 5:  # online within last 5 minutes
                    should_resolve = True

            elif alert.alert_type == 'hashrate':
                baseline = (alert.details or {}).get('baseline_hashrate')
                if baseline and metric.hashrate_ths:
                    if metric.hashrate_ths >= baseline * 0.95:  # back to 95% of baseline
                        should_resolve = True

            if should_resolve:
                alert.status = 'auto_resolved'
                alert.resolved_at = datetime.utcnow()
                alert.resolution_note = 'Condition automatically cleared'
                logger.info(f"Auto-resolved alert {alert.id} for {alert.miner_ip}")

        self.session.commit()

    def acknowledge_alert(self, alert_id: int, user: str = 'system') -> bool:
        """Acknowledge an alert."""
        alert = self.session.query(Alert).filter(Alert.id == alert_id).first()
        if alert and alert.status == 'active':
            alert.status = 'acknowledged'
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = user
            self.session.commit()
            return True
        return False

    def resolve_alert(self, alert_id: int, note: str = None, user: str = 'system') -> bool:
        """Manually resolve an alert."""
        alert = self.session.query(Alert).filter(Alert.id == alert_id).first()
        if alert and alert.status in ['active', 'acknowledged']:
            alert.status = 'resolved'
            alert.resolved_at = datetime.utcnow()
            alert.resolution_note = note
            self.session.commit()
            return True
        return False


def create_default_rules(session=None):
    """Create default alert rules if none exist."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        existing = session.query(AlertRule).count()
        if existing > 0:
            return

        default_rules = [
            AlertRule(
                name="High Temperature Alert",
                description="Alert when miner temperature exceeds threshold",
                rule_type="temp",
                thresholds={"temp_c": TEMP_THRESHOLD},
                severity="warning",
                cooldown_minutes=30
            ),
            AlertRule(
                name="Miner Offline",
                description="Alert when miner hasn't reported in 10 minutes",
                rule_type="offline",
                thresholds={"max_age_minutes": 10},
                severity="critical",
                cooldown_minutes=60
            ),
            AlertRule(
                name="Hashrate Drop",
                description="Alert when hashrate drops significantly",
                rule_type="hashrate",
                thresholds={"drop_threshold": HASHRATE_DROP_THRESHOLD},
                severity="warning",
                cooldown_minutes=45
            ),
            AlertRule(
                name="Fan Speed Low",
                description="Alert when fan speed is too low",
                rule_type="fan",
                thresholds={"min_rpm": 2000},
                severity="warning",
                cooldown_minutes=30
            )
        ]

        for rule in default_rules:
            session.add(rule)

        session.commit()
        logger.info(f"Created {len(default_rules)} default alert rules")

    finally:
        if close_session:
            session.close()
