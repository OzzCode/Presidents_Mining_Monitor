"""API endpoints for alerts and profitability features."""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc, func
import logging

from core.db import SessionLocal, Alert, AlertRule, ProfitabilitySnapshot, Miner, Metric
from core.alert_engine import AlertEngine, create_default_rules
from core.notification_service import NotificationService
from core.profitability import ProfitabilityEngine

logger = logging.getLogger(__name__)

alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')
profitability_bp = Blueprint('profitability', __name__, url_prefix='/api/profitability')


# ============================================================================
# ALERT ENDPOINTS
# ============================================================================

@alerts_bp.route('/', methods=['GET'])
def get_alerts():
    """
    Get alerts with optional filters.
    Query params: 
      - status: active, acknowledged, resolved, auto_resolved (comma-separated)
      - severity: info, warning, critical (comma-separated)
      - miner_ip: filter by specific miner
      - alert_type: offline, temp, hashrate, fan, power
      - limit: max results (default 100)
      - since: ISO8601 datetime
    """
    status_filter = request.args.get('status')
    severity_filter = request.args.get('severity')
    miner_ip = request.args.get('miner_ip')
    alert_type = request.args.get('alert_type')
    limit = min(int(request.args.get('limit', 100)), 1000)
    since = request.args.get('since')

    session = SessionLocal()
    try:
        query = session.query(Alert)

        if status_filter:
            statuses = [s.strip() for s in status_filter.split(',')]
            query = query.filter(Alert.status.in_(statuses))

        if severity_filter:
            severities = [s.strip() for s in severity_filter.split(',')]
            query = query.filter(Alert.severity.in_(severities))

        if miner_ip:
            query = query.filter(Alert.miner_ip == miner_ip)

        if alert_type:
            query = query.filter(Alert.alert_type == alert_type)

        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query = query.filter(Alert.created_at >= since_dt)
            except ValueError:
                return jsonify({'error': 'Invalid since datetime format'}), 400

        alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()

        return jsonify({
            'ok': True,
            'count': len(alerts),
            'alerts': [_serialize_alert(a) for a in alerts]
        })

    finally:
        session.close()


@alerts_bp.route('/<int:alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Get a specific alert by ID."""
    session = SessionLocal()
    try:
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404

        return jsonify({
            'ok': True,
            'alert': _serialize_alert(alert)
        })
    finally:
        session.close()


@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """
    Acknowledge an alert.
    Body: { "user": "username" } (optional)
    """
    data = request.get_json(silent=True) or {}
    user = data.get('user', 'web_user')

    with AlertEngine() as engine:
        success = engine.acknowledge_alert(alert_id, user)

    if success:
        return jsonify({'ok': True, 'message': 'Alert acknowledged'})
    else:
        return jsonify({'ok': False, 'error': 'Failed to acknowledge alert'}), 400


@alerts_bp.route('/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """
    Resolve an alert.
    Body: { "note": "resolution note", "user": "username" } (optional)
    """
    data = request.get_json(silent=True) or {}
    note = data.get('note')
    user = data.get('user', 'web_user')

    with AlertEngine() as engine:
        success = engine.resolve_alert(alert_id, note, user)

    if success:
        return jsonify({'ok': True, 'message': 'Alert resolved'})
    else:
        return jsonify({'ok': False, 'error': 'Failed to resolve alert'}), 400


@alerts_bp.route('/summary', methods=['GET'])
def get_alerts_summary():
    """Get summary statistics of alerts."""
    session = SessionLocal()
    try:
        total = session.query(Alert).count()
        active = session.query(Alert).filter(Alert.status == 'active').count()
        acknowledged = session.query(Alert).filter(Alert.status == 'acknowledged').count()
        resolved = session.query(Alert).filter(Alert.status == 'resolved').count()

        # Count by severity
        critical = session.query(Alert).filter(
            Alert.severity == 'critical',
            Alert.status.in_(['active', 'acknowledged'])
        ).count()

        warning = session.query(Alert).filter(
            Alert.severity == 'warning',
            Alert.status.in_(['active', 'acknowledged'])
        ).count()

        # Recent alerts (last 24h)
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        recent = session.query(Alert).filter(Alert.created_at >= cutoff_24h).count()

        return jsonify({
            'ok': True,
            'summary': {
                'total': total,
                'active': active,
                'acknowledged': acknowledged,
                'resolved': resolved,
                'critical_active': critical,
                'warning_active': warning,
                'last_24h': recent
            }
        })
    finally:
        session.close()


@alerts_bp.route('/check', methods=['POST'])
def trigger_alert_check():
    """Manually trigger alert checking for all miners."""
    try:
        with AlertEngine() as engine:
            new_alerts = engine.check_all_miners()

        # Send notifications for new alerts
        if new_alerts:
            notifier = NotificationService()
            notifier.batch_notify(new_alerts)

        return jsonify({
            'ok': True,
            'message': f'Alert check completed, {len(new_alerts)} new alerts',
            'new_alerts': [_serialize_alert(a) for a in new_alerts]
        })
    except Exception as e:
        logger.exception("Alert check failed", exc_info=e)
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================================
# ALERT RULES ENDPOINTS
# ============================================================================

@alerts_bp.route('/rules', methods=['GET'])
def get_alert_rules():
    """Get all alert rules."""
    session = SessionLocal()
    try:
        rules = session.query(AlertRule).all()
        return jsonify({
            'ok': True,
            'count': len(rules),
            'rules': [_serialize_alert_rule(r) for r in rules]
        })
    finally:
        session.close()


@alerts_bp.route('/rules/<int:rule_id>', methods=['GET'])
def get_alert_rule(rule_id):
    """Get a specific alert rule."""
    session = SessionLocal()
    try:
        rule = session.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return jsonify({'error': 'Rule not found'}), 404

        return jsonify({
            'ok': True,
            'rule': _serialize_alert_rule(rule)
        })
    finally:
        session.close()


@alerts_bp.route('/rules', methods=['POST'])
def create_alert_rule():
    """
    Create a new alert rule.
    Body: {
        "name": str,
        "description": str (optional),
        "rule_type": "offline" | "temp" | "hashrate" | "fan" | "power",
        "enabled": bool,
        "thresholds": dict,
        "severity": "info" | "warning" | "critical",
        "cooldown_minutes": int,
        "notify_email": bool,
        "notify_webhook": bool,
        "webhook_url": str (optional),
        "miner_ip": str (optional),
        "model_filter": str (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    required_fields = ['name', 'rule_type', 'thresholds']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    session = SessionLocal()
    try:
        rule = AlertRule(
            name=data['name'],
            description=data.get('description'),
            rule_type=data['rule_type'],
            enabled=data.get('enabled', True),
            thresholds=data['thresholds'],
            severity=data.get('severity', 'warning'),
            cooldown_minutes=data.get('cooldown_minutes', 30),
            notify_email=data.get('notify_email', True),
            notify_webhook=data.get('notify_webhook', False),
            webhook_url=data.get('webhook_url'),
            miner_ip=data.get('miner_ip'),
            model_filter=data.get('model_filter')
        )

        session.add(rule)
        session.commit()
        session.refresh(rule)

        return jsonify({
            'ok': True,
            'message': 'Alert rule created',
            'rule': _serialize_alert_rule(rule)
        }), 201

    except Exception as e:
        session.rollback()
        logger.exception("Failed to create alert rule", exc_info=e)
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@alerts_bp.route('/rules/<int:rule_id>', methods=['PUT'])
def update_alert_rule(rule_id):
    """Update an existing alert rule."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    session = SessionLocal()
    try:
        rule = session.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return jsonify({'error': 'Rule not found'}), 404

        # Update fields
        updatable_fields = [
            'name', 'description', 'rule_type', 'enabled', 'thresholds',
            'severity', 'cooldown_minutes', 'notify_email', 'notify_webhook',
            'webhook_url', 'miner_ip', 'model_filter'
        ]

        for field in updatable_fields:
            if field in data:
                setattr(rule, field, data[field])

        rule.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(rule)

        return jsonify({
            'ok': True,
            'message': 'Alert rule updated',
            'rule': _serialize_alert_rule(rule)
        })

    except Exception as e:
        session.rollback()
        logger.exception("Failed to update alert rule", exc_info=e)
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@alerts_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
def delete_alert_rule(rule_id):
    """Delete an alert rule."""
    session = SessionLocal()
    try:
        rule = session.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return jsonify({'error': 'Rule not found'}), 404

        session.delete(rule)
        session.commit()

        return jsonify({
            'ok': True,
            'message': 'Alert rule deleted'
        })

    except Exception as e:
        session.rollback()
        logger.exception("Failed to delete alert rule", exc_info=e)
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@alerts_bp.route('/rules/init-defaults', methods=['POST'])
def init_default_rules():
    """Initialize default alert rules."""
    try:
        create_default_rules()
        return jsonify({
            'ok': True,
            'message': 'Default alert rules initialized'
        })
    except Exception as e:
        logger.exception("Failed to initialize default rules", exc_info=e)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PROFITABILITY ENDPOINTS
# ============================================================================

@profitability_bp.route('/active-miners', methods=['GET'])
def get_active_miners():
    """
    Get list of currently active miners.
    Query params:
      - hours: Hours threshold for considering a miner active (default 1)
    """
    hours = int(request.args.get('hours', 1))

    try:
        with ProfitabilityEngine() as engine:
            active_miners = engine.get_active_miners(hours_threshold=hours)

        return jsonify({
            'ok': True,
            'count': len(active_miners),
            'hours_threshold': hours,
            'active_miners': active_miners
        })

    except Exception as e:
        logger.exception("Failed to fetch active miners", exc_info=e)
        return jsonify({'error': str(e)}), 500


@profitability_bp.route('/current', methods=['GET'])
def get_current_profitability():
    """
    Get current profitability for a specific miner or entire fleet.
    Query params:
      - miner_ip: IP address (optional, if omitted returns fleet-wide)
      - active_only: If true, only consider miners active in the last hour (default false)
    """
    miner_ip = request.args.get('miner_ip')
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    try:
        with ProfitabilityEngine() as engine:
            if miner_ip:
                result = engine.calculate_miner_profitability(miner_ip)
                if not result:
                    return jsonify({'error': 'Insufficient data for miner'}), 404
            else:
                if active_only:
                    # Calculate profitability only for active miners
                    active_miners = engine.get_active_miners(hours_threshold=1)
                    if not active_miners:
                        return jsonify({'error': 'No active miners found'}), 404

                    # Get metrics only for active miners
                    latest_subq = (
                        engine.session.query(
                            Metric.miner_ip.label('ip'),
                            func.max(Metric.timestamp).label('last_ts')
                        ).filter(Metric.miner_ip.in_(active_miners)).group_by(Metric.miner_ip).subquery()
                    )

                    metrics = (
                        engine.session.query(Metric)
                        .join(latest_subq, and_(
                            Metric.miner_ip == latest_subq.c.ip,
                            Metric.timestamp == latest_subq.c.last_ts
                        ))
                        .all()
                    )

                    if not metrics:
                        return jsonify({'error': 'No data for active miners'}), 404

                    # Get miner metadata for active miners
                    miners_dict = {}
                    miner_ips = [m.miner_ip for m in metrics]
                    if miner_ips:
                        miners = engine.session.query(Miner).filter(Miner.miner_ip.in_(miner_ips)).all()
                        miners_dict = {m.miner_ip: m for m in miners}

                    # Get BTC price and difficulty
                    btc_price = engine.get_btc_price()
                    network_difficulty = engine.get_network_difficulty()

                    if not btc_price:
                        return jsonify({'error': 'Could not fetch BTC price'}), 502

                    # Aggregate metrics for active miners only
                    total_hashrate = 0.0
                    total_power = 0.0
                    weighted_power_cost = 0.0
                    miner_count = 0

                    for metric in metrics:
                        if not metric.hashrate_ths or not metric.power_w:
                            continue

                        miner = miners_dict.get(metric.miner_ip)
                        power_cost = engine.default_power_cost
                        if miner and miner.power_price_usd_per_kwh:
                            power_cost = miner.power_price_usd_per_kwh

                        total_hashrate += metric.hashrate_ths
                        total_power += metric.power_w
                        weighted_power_cost += metric.power_w * power_cost
                        miner_count += 1

                    if total_power == 0:
                        return jsonify({'error': 'No valid metrics for active miners'}), 404

                    # Calculate average power cost weighted by power consumption
                    avg_power_cost = weighted_power_cost / total_power

                    # Calculate fleet profitability for active miners only
                    result = engine._calculate_profitability(
                        hashrate_ths=total_hashrate,
                        power_w=total_power,
                        btc_price=btc_price,
                        power_cost=avg_power_cost,
                        network_difficulty=network_difficulty
                    )

                    result['miner_count'] = miner_count
                    result['active_only'] = True
                    result['active_miners'] = active_miners
                else:
                    result = engine.calculate_fleet_profitability()
                    if not result:
                        return jsonify({'error': 'No fleet data available'}), 404

        return jsonify({
            'ok': True,
            'profitability': _serialize_profitability(result)
        })

    except Exception as e:
        logger.exception("Profitability calculation failed", exc_info=e)
        return jsonify({'error': str(e)}), 500


@profitability_bp.route('/history', methods=['GET'])
def get_profitability_history():
    """
    Get historical profitability data.
    Query params:
      - miner_ip: IP address (optional, if omitted returns fleet-wide)
      - days: number of days of history (default 7, max 90)
      - active_only: If true, only consider miners active in the last hour (default false)
    """
    miner_ip = request.args.get('miner_ip')
    days = min(int(request.args.get('days', 7)), 90)
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    try:
        with ProfitabilityEngine() as engine:
            aggregated_mode = False
            if active_only and not miner_ip:
                # Get active miners for fleet-wide history filtering
                active_miners = engine.get_active_miners(hours_threshold=1)
                if not active_miners:
                    # Fallback to fleet-wide snapshots so the chart still renders
                    history = engine.get_profitability_history(None, days)
                    aggregated_mode = False
                else:
                    # Get snapshots only for active miners and aggregate them by hour
                    cutoff = datetime.utcnow() - timedelta(days=days)

                    snapshots = (
                        engine.session.query(ProfitabilitySnapshot)
                        .filter(
                            and_(
                                ProfitabilitySnapshot.timestamp >= cutoff,
                                ProfitabilitySnapshot.miner_ip.in_(active_miners)
                            )
                        )
                        .order_by(ProfitabilitySnapshot.timestamp.asc())
                        .all()
                    )

                    # Group by timestamp and aggregate
                    history_by_time = {}
                    for snapshot in snapshots:
                        timestamp = snapshot.timestamp.replace(minute=0, second=0, microsecond=0)
                        if timestamp not in history_by_time:
                            history_by_time[timestamp] = {
                                'timestamp': timestamp,
                                'btc_price_usd': snapshot.btc_price_usd,
                                'network_difficulty': snapshot.network_difficulty,
                                'total_hashrate': 0,
                                'total_power': 0,
                                'total_cost': 0,
                                'total_revenue': 0,
                                'miner_count': 0
                            }

                        entry = history_by_time[timestamp]
                        if snapshot.hashrate_ths:
                            entry['total_hashrate'] += snapshot.hashrate_ths
                        if snapshot.power_w:
                            entry['total_power'] += snapshot.power_w
                        if snapshot.daily_power_cost_usd:
                            entry['total_cost'] += snapshot.daily_power_cost_usd
                        if snapshot.estimated_revenue_usd_per_day:
                            entry['total_revenue'] += snapshot.estimated_revenue_usd_per_day
                        entry['miner_count'] += 1

                    # Convert to list and calculate aggregated values
                    aggregated_history = []
                    for entry in history_by_time.values():
                        daily_profit = entry['total_revenue'] - entry['total_cost']
                        aggregated_history.append({
                            'timestamp': entry['timestamp'],
                            'daily_profit_usd': daily_profit,
                            'estimated_revenue_usd_per_day': entry['total_revenue'],
                            'daily_power_cost_usd': entry['total_cost'],
                            'hashrate_ths': entry['total_hashrate'],
                            'power_w': entry['total_power'],
                            'btc_price_usd': entry['btc_price_usd'],
                            'network_difficulty': entry['network_difficulty'],
                            'miner_count': entry['miner_count']
                        })

                    history = sorted(aggregated_history, key=lambda x: x['timestamp'])
                    aggregated_mode = True
            else:
                history = engine.get_profitability_history(miner_ip, days)
                aggregated_mode = False

        # Prepare history payload depending on data type
        history_payload = []
        if active_only and not miner_ip:
            # Aggregated dicts already built above; normalize timestamp format
            for entry in history:
                item = dict(entry)
                ts = item.get('timestamp')
                item['timestamp'] = ts.isoformat() + 'Z' if ts else None
                history_payload.append(item)
        else:
            # ORM snapshots → serialize
            history_payload = [_serialize_profitability_snapshot(s) for s in history]

        return jsonify({
            'ok': True,
            'count': len(history_payload),
            'history': history_payload,
            'active_only': active_only if not miner_ip else False
        })

    except Exception as e:
        logger.exception("Failed to fetch profitability history", exc_info=e)
        return jsonify({'error': str(e)}), 500


@profitability_bp.route('/snapshot', methods=['POST'])
def create_profitability_snapshot():
    """
    Manually trigger profitability snapshot calculation and save it.
    Query params:
      - miner_ip: IP address (optional, if omitted creates fleet-wide snapshot)
    """
    miner_ip = request.args.get('miner_ip')

    try:
        with ProfitabilityEngine() as engine:
            if miner_ip:
                result = engine.calculate_miner_profitability(miner_ip)
                if result:
                    engine.save_snapshot(result, miner_ip)
            else:
                result = engine.calculate_fleet_profitability()
                if result:
                    engine.save_snapshot(result, None)

            if not result:
                return jsonify({'error': 'Failed to calculate profitability'}), 500

        return jsonify({
            'ok': True,
            'message': 'Snapshot saved',
            'profitability': _serialize_profitability(result)
        })

    except Exception as e:
        logger.exception("Failed to create profitability snapshot", exc_info=e)
        return jsonify({'error': str(e)}), 500


@profitability_bp.route('/btc-price', methods=['GET'])
def get_btc_price():
    """Get current BTC price."""
    try:
        with ProfitabilityEngine() as engine:
            price = engine.get_btc_price()

        if price is None:
            return jsonify({'error': 'Failed to fetch BTC price'}), 502

        return jsonify({
            'ok': True,
            'btc_price_usd': price,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    except Exception as e:
        logger.exception("Failed to fetch BTC price", exc_info=e)
        return jsonify({'error': str(e)}), 500


@profitability_bp.route('/network-difficulty', methods=['GET'])
def get_network_difficulty():
    """Get current network difficulty."""
    try:
        with ProfitabilityEngine() as engine:
            difficulty = engine.get_network_difficulty()

        return jsonify({
            'ok': True,
            'network_difficulty': difficulty,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    except Exception as e:
        logger.exception("Failed to fetch network difficulty", exc_info=e)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SERIALIZATION HELPERS
# ============================================================================

def _serialize_alert(alert: Alert) -> dict:
    """Serialize Alert model to dict."""
    return {
        'id': alert.id,
        'created_at': alert.created_at.isoformat() + 'Z' if alert.created_at else None,
        'updated_at': alert.updated_at.isoformat() + 'Z' if alert.updated_at else None,
        'rule_id': alert.rule_id,
        'miner_ip': alert.miner_ip,
        'alert_type': alert.alert_type,
        'severity': alert.severity,
        'message': alert.message,
        'details': alert.details,
        'status': alert.status,
        'acknowledged_at': alert.acknowledged_at.isoformat() + 'Z' if alert.acknowledged_at else None,
        'acknowledged_by': alert.acknowledged_by,
        'resolved_at': alert.resolved_at.isoformat() + 'Z' if alert.resolved_at else None,
        'resolution_note': alert.resolution_note,
        'notified_at': alert.notified_at.isoformat() + 'Z' if alert.notified_at else None,
        'notification_status': alert.notification_status
    }


def _serialize_alert_rule(rule: AlertRule) -> dict:
    """Serialize AlertRule model to dict."""
    return {
        'id': rule.id,
        'created_at': rule.created_at.isoformat() + 'Z' if rule.created_at else None,
        'updated_at': rule.updated_at.isoformat() + 'Z' if rule.updated_at else None,
        'name': rule.name,
        'description': rule.description,
        'rule_type': rule.rule_type,
        'enabled': rule.enabled,
        'miner_ip': rule.miner_ip,
        'model_filter': rule.model_filter,
        'tags_filter': rule.tags_filter,
        'thresholds': rule.thresholds,
        'severity': rule.severity,
        'cooldown_minutes': rule.cooldown_minutes,
        'notify_email': rule.notify_email,
        'notify_webhook': rule.notify_webhook,
        'webhook_url': rule.webhook_url,
        'auto_action': rule.auto_action
    }


def _serialize_profitability(data: dict) -> dict:
    """Serialize profitability calculation result."""
    return {
        'timestamp': data.get('timestamp').isoformat() + 'Z' if data.get('timestamp') else None,
        'miner_ip': data.get('miner_ip'),
        'miner_count': data.get('miner_count'),
        'btc_price_usd': round(data.get('btc_price_usd', 0), 2),
        'network_difficulty': data.get('network_difficulty'),
        'hashrate_ths': round(data.get('hashrate_ths', 0), 2),
        'power_w': round(data.get('power_w', 0), 2),
        'power_cost_usd_per_kwh': round(data.get('power_cost_usd_per_kwh', 0), 4),
        'daily_power_kwh': round(data.get('daily_power_kwh', 0), 2),
        'daily_power_cost_usd': round(data.get('daily_power_cost_usd', 0), 2),
        'estimated_btc_per_day': data.get('estimated_btc_per_day'),
        'estimated_revenue_usd_per_day': round(data.get('estimated_revenue_usd_per_day', 0), 2),
        'daily_profit_usd': round(data.get('daily_profit_usd', 0), 2),
        'profit_margin_pct': round(data.get('profit_margin_pct', 0), 2),
        'break_even_btc_price': round(data.get('break_even_btc_price', 0), 2),
        'efficiency_j_per_th': round(data.get('efficiency_j_per_th', 0), 2),
        'monthly_profit_usd': round(data.get('monthly_profit_usd', 0), 2),
        'yearly_profit_usd': round(data.get('yearly_profit_usd', 0), 2),
        'monthly_btc': data.get('monthly_btc'),
        'yearly_btc': data.get('yearly_btc')
    }


def _serialize_profitability_snapshot(snapshot: ProfitabilitySnapshot) -> dict:
    """Serialize ProfitabilitySnapshot model to dict."""
    return {
        'id': snapshot.id,
        'timestamp': snapshot.timestamp.isoformat() + 'Z' if snapshot.timestamp else None,
        'miner_ip': snapshot.miner_ip,
        'btc_price_usd': round(snapshot.btc_price_usd, 2) if snapshot.btc_price_usd else None,
        'network_difficulty': snapshot.network_difficulty,
        'hashrate_ths': round(snapshot.hashrate_ths, 2) if snapshot.hashrate_ths else None,
        'power_w': round(snapshot.power_w, 2) if snapshot.power_w else None,
        'power_cost_usd_per_kwh': round(snapshot.power_cost_usd_per_kwh,
                                        4) if snapshot.power_cost_usd_per_kwh else None,
        'daily_power_cost_usd': round(snapshot.daily_power_cost_usd, 2) if snapshot.daily_power_cost_usd else None,
        'estimated_btc_per_day': snapshot.estimated_btc_per_day,
        'estimated_revenue_usd_per_day': round(snapshot.estimated_revenue_usd_per_day,
                                               2) if snapshot.estimated_revenue_usd_per_day else None,
        'daily_profit_usd': round(snapshot.daily_profit_usd, 2) if snapshot.daily_profit_usd else None,
        'profit_margin_pct': round(snapshot.profit_margin_pct, 2) if snapshot.profit_margin_pct else None,
        'break_even_btc_price': round(snapshot.break_even_btc_price, 2) if snapshot.break_even_btc_price else None
    }
