from flask import Blueprint, render_template, request, jsonify
from auth import login_required

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
                    # Extract model and firmware version using the new _normalize_model function
                    from helpers.utils import _normalize_model
                    raw_model_name = models.get(ip, '')
                    model_name, firmware_version = _normalize_model(raw_model_name, extract_firmware=True)
                    
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
                    
                    try:
                        # Add debug logging
                        import logging
                        logging.basicConfig(level=logging.DEBUG)
                        logger = logging.getLogger(__name__)
                        logger.debug(f"Processing miner: IP={ip}, Model='{model_name}', Firmware='{firmware_version}'")
                        
                        # Get efficiency data with multiple fallback strategies
                        # Use the raw model name for lookups as it includes firmware info if present
                        nominal_ths, csv_eff = 0.0, 0.0
                        
                        # Try to get from CSV first (uses raw model name internally)
                        nominal_ths, csv_eff = csv_efficiency_for_model(raw_model_name)
                        logger.debug(f"CSV lookup - Model: '{model_name}', Result: TH/s={nominal_ths}, J/TH={csv_eff}")
                        
                        # If CSV lookup failed or returned zeros, try the full efficiency lookup
                        if not (nominal_ths and csv_eff) and model_name:
                            eff = efficiency_for_model(raw_model_name)
                            logger.debug(f"Efficiency lookup - Model: '{model_name}', Result: {eff} J/TH")
                            if eff > 0:
                                csv_eff = eff
                                # If we still don't have nominal THs, try to estimate
                                if not nominal_ths:
                                    # Try to extract TH/s from model name (e.g., 'S19 Pro 110T' -> 110)
                                    if model_name:
                                        ths_match = re.search(r'(\d+)\s*(?:t|th|ths|terahash)', model_name, re.IGNORECASE)
                                        if ths_match:
                                            nominal_ths = float(ths_match.group(1))
                                            logger.debug(f"Extracted TH/s from model name: {nominal_ths}")
                                    
                                    # Default fallback if we couldn't determine from model name
                                    if not nominal_ths:
                                        nominal_ths = 100.0  # Reasonable default
                                        logger.debug(f"Using default TH/s: {nominal_ths}")
                        
                        logger.debug(f"Final values - TH/s: {nominal_ths}, J/TH: {csv_eff}")
                        
                        # Create the miner with the best data we have
                        miner = Miner(
                            miner_ip=ip,
                            vendor=vendor,
                            model=model_name or None,
                            firmware_version=firmware_version,
                            nominal_ths=float(nominal_ths) if nominal_ths else None,
                            nominal_efficiency_j_per_th=float(csv_eff) if csv_eff else None
                        )
                    except Exception as e:
                        # Log the error but continue with defaults
                        import logging
                        logging.error(f"Error creating miner {ip}: {str(e)}")
                        miner = Miner(
                            miner_ip=ip,
                            vendor=vendor,
                            model=model_name or None,
                            nominal_ths=100.0,  # Default values
                            nominal_efficiency_j_per_th=EFFICIENCY_J_PER_TH
                        )
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
@login_required
def index():
    ip = request.args.get('ip')
    return render_template('dashboard.html', ip=ip)


@dash_bp.route('/miners')
@login_required
def show_miners():
    return render_template('miners.html')


@dash_bp.route('/pools')
@login_required
def pools_page():
    return render_template('pools.html')


@dash_bp.route("/logs")
@login_required
def logs_page():
    return render_template("logs.html")


@dash_bp.route('/alerts')
@login_required
def alerts_page():
    return render_template('alerts.html')


@dash_bp.route('/profitability')
@login_required
def profitability_page():
    return render_template('profitability.html')


@dash_bp.route('/analytics')
@login_required
def analytics_page():
    return render_template('analytics.html')


@dash_bp.route('/electricity')
@login_required
def electricity_page():
    """Electricity cost management page."""
    return render_template('electricity.html')


@dash_bp.route('/remote')
@login_required
def remote_control_page():
    """Remote control management page."""
    return render_template('remote_control.html')
