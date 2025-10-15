from flask import Blueprint, render_template, request, jsonify

dash_bp = Blueprint('dashboard', __name__)

api_bp = Blueprint("api", __name__)


def get_miners():
    """
    Return the latest-known status per discovered miner using DB data, enriched with model when available.

    Output: list of dicts with keys
      - is_stale (bool)
      - age_sec (int)
      - status (str)
      - model (str)
      - ip (str)
      - last_seen (ISO8601 string with Z)
      - est_power_w (float)  # estimated using CSV J/TH and hashrate
    """
    from datetime import datetime, timezone
    from sqlalchemy import func, and_
    from core.db import SessionLocal, Metric, Miner
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from core.miner import MinerClient
    from helpers.utils import csv_efficiency_for_model, efficiency_for_model

    # Freshness thresholds (seconds). Keep in sync with static/js/miners.js
    # REFRESH_INTERVAL in JS is 15s; JS marks:
    #  <= 2x interval => green (Fresh)
    #  <= 5x interval => yellow (Lagging)
    #  >  5x interval => red (Stale)
    INTERVAL = 15
    LAGGING = 5 * INTERVAL

    now = datetime.now(timezone.utc)

    s = SessionLocal()
    try:
        latest = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts')
            ).group_by(Metric.miner_ip).subquery()
        )

        rows = (
            s.query(Metric)
            .join(latest, and_(Metric.miner_ip == latest.c.ip,
                               Metric.timestamp == latest.c.last_ts))
            .order_by(Metric.miner_ip.asc())
            .all()
        )

        # Best-effort model lookup in parallel
        models = {}
        ips = [m.miner_ip for m in rows]
        if ips:
            def _fetch(ip):
                try:
                    return ip, MinerClient(ip).fetch_normalized().get('model', '')
                except Exception:
                    return ip, ''

            with ThreadPoolExecutor(max_workers=min(8, len(ips))) as ex:
                for fut in as_completed([ex.submit(_fetch, ip) for ip in ips]):
                    ip, model = fut.result()
                    models[ip] = model

        # Load existing Miner metadata and create rows for new IPs
        miners_by_ip = {}
        if ips:
            for miner in s.query(Miner).filter(Miner.miner_ip.in_(ips)).all():
                miners_by_ip[miner.miner_ip] = miner
            created_any = False
            for ip in ips:
                if ip not in miners_by_ip:
                    model_name = models.get(ip, '')
                    # Guess vendor from model prefix
                    vendor = None
                    if model_name:
                        low = model_name.lower()
                        if 'antminer' in low or 'bitmain' in low:
                            vendor = 'Bitmain'
                        elif 'whatsminer' in low or 'microbt' in low:
                            vendor = 'MicroBT'
                        elif 'avalon' in low or 'canaan' in low:
                            vendor = 'Canaan'
                    # CSV-derived defaults
                    nominal_ths, csv_eff = csv_efficiency_for_model(model_name)
                    miner = Miner(miner_ip=ip,
                                  vendor=vendor,
                                  model=model_name or None,
                                  nominal_ths=nominal_ths or None,
                                  nominal_efficiency_j_per_th=csv_eff or None)
                    s.add(miner)
                    miners_by_ip[ip] = miner
                    created_any = True
            if created_any:
                try:
                    s.commit()
                except Exception:
                    s.rollback()

        out = []
        for m in rows:
            ts = m.timestamp
            # Ensure aware UTC for age computation
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = int((now - ts).total_seconds())

            if age <= 2 * INTERVAL:
                status = 'Active'
            elif age <= LAGGING:
                status = 'Lagging'
            else:
                status = 'Stale'

            # Estimate power using CSV efficiency and hashrate
            model_name = models.get(m.miner_ip, '')
            nominal_ths, csv_eff = csv_efficiency_for_model(model_name)
            # Prefer latest measured hashrate if available; otherwise CSV nominal
            hr_ths = None
            try:
                if m.hashrate_ths is not None:
                    hr_ths = float(m.hashrate_ths)
            except Exception:
                hr_ths = None
            if not hr_ths or hr_ths <= 0:
                hr_ths = nominal_ths if nominal_ths > 0 else None
            # Choose efficiency: CSV first, else config mapping, else default
            eff_j_per_th = csv_eff if (csv_eff and csv_eff > 0) else efficiency_for_model(model_name)
            est_power = None
            if hr_ths and eff_j_per_th:
                try:
                    est_power = round(hr_ths * eff_j_per_th, 1)
                except Exception:
                    est_power = None

            miner_meta = miners_by_ip.get(m.miner_ip)
            out.append({
                'is_stale': age > LAGGING,
                'age_sec': age,
                'status': status,
                'model': (miner_meta.model if (miner_meta and miner_meta.model) else model_name),
                'ip': m.miner_ip,
                'last_seen': ts.isoformat().replace('+00:00', 'Z'),
                'est_power_w': est_power,
                # Metadata enrichment (present when available)
                'vendor': getattr(miner_meta, 'vendor', None) if miner_meta else None,
                'hostname': getattr(miner_meta, 'hostname', None) if miner_meta else None,
                'rack': getattr(miner_meta, 'rack', None) if miner_meta else None,
                'row': getattr(miner_meta, 'row', None) if miner_meta else None,
                'location': getattr(miner_meta, 'location', None) if miner_meta else None,
                'room': getattr(miner_meta, 'room', None) if miner_meta else None,
                'owner': getattr(miner_meta, 'owner', None) if miner_meta else None,
                'notes': getattr(miner_meta, 'notes', None) if miner_meta else None,
                'nominal_ths': getattr(miner_meta, 'nominal_ths', None) if miner_meta else nominal_ths,
                'nominal_efficiency_j_per_th': getattr(miner_meta, 'nominal_efficiency_j_per_th',
                                                       None) if miner_meta else csv_eff,
                'power_price_usd_per_kwh': getattr(miner_meta, 'power_price_usd_per_kwh', None) if miner_meta else None,
                'tags': getattr(miner_meta, 'tags', None) if miner_meta else None,
            })
        return out
    finally:
        s.close()


@api_bp.get("/miners")
def miners():
    miners = get_miners()
    # Ensure a consistent response contract expected by miners.js
    return jsonify({"miners": miners})


@dash_bp.route('/')
def index():
    ip = request.args.get('ip')
    return render_template('dashboard.html', ip=ip)


@dash_bp.route('/miners')
def show_miners():
    return render_template('miners.html')


@dash_bp.route('/pools')
def pools_page():
    return render_template('pools.html')


@dash_bp.route("/logs")
def logs_page():
    return render_template("logs.html")


@dash_bp.route('/returns')
def returns_page():
    return render_template('returns.html')


@dash_bp.route('/alerts')
def alerts_page():
    return render_template('alerts.html')


@dash_bp.route('/profitability')
def profitability_page():
    return render_template('profitability.html')


@dash_bp.route('/analytics')
def analytics_page():
    return render_template('analytics.html')
