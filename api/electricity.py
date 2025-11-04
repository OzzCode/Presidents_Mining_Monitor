"""
API endpoints for electricity cost tracking and management.
"""

from flask import Blueprint, request, jsonify, render_template
from sqlalchemy import and_, func
from core.db import SessionLocal, ElectricityRate, ElectricityCost, Metric, Miner
from core.electricity import ElectricityCostService, create_default_rates
import datetime as dt

bp = Blueprint("electricity_api", __name__, url_prefix="/api/electricity")


def estimate_costs_from_fleet(session, location=None):
    """Estimate costs based on current fleet power consumption."""
    # Get active rate
    rate = ElectricityCostService.get_active_rate(session, location)

    if not rate:
        return {
            "total_cost_usd": 0.0,
            "total_kwh": 0.0,
            "avg_rate_usd_per_kwh": 0.0,
            "num_records": 0,
            "tou_breakdown_usd": None,
            "period_start": dt.datetime.utcnow() - dt.timedelta(days=30),
            "period_end": dt.datetime.utcnow(),
            "estimated": True
        }

    # Get recent metrics to estimate power consumption
    cutoff = dt.datetime.utcnow() - dt.timedelta(hours=1)

    # Query miners with location filter if provided
    miner_query = session.query(Miner)
    if location:
        miner_query = miner_query.filter(Miner.location == location)

    miners = miner_query.all()
    miner_ips = [m.miner_ip for m in miners] if miners else []

    # Get latest metrics for these miners
    if miner_ips:
        metrics_query = session.query(Metric).filter(
            and_(
                Metric.miner_ip.in_(miner_ips),
                Metric.timestamp >= cutoff
            )
        )
    else:
        # If no location filter, get all recent metrics
        metrics_query = session.query(Metric).filter(Metric.timestamp >= cutoff)

    # Get latest metric per miner
    from sqlalchemy.sql import func as sql_func
    subq = session.query(
        Metric.miner_ip,
        sql_func.max(Metric.timestamp).label('max_ts')
    ).filter(Metric.timestamp >= cutoff).group_by(Metric.miner_ip).subquery()

    latest_metrics = session.query(Metric).join(
        subq,
        and_(
            Metric.miner_ip == subq.c.miner_ip,
            Metric.timestamp == subq.c.max_ts
        )
    ).all()

    # Calculate total fleet power
    total_power_w = sum(m.power_w for m in latest_metrics if m.power_w)

    if total_power_w == 0:
        return {
            "total_cost_usd": 0.0,
            "total_kwh": 0.0,
            "avg_rate_usd_per_kwh": 0.0,
            "num_records": 0,
            "tou_breakdown_usd": None,
            "period_start": dt.datetime.utcnow() - dt.timedelta(days=30),
            "period_end": dt.datetime.utcnow(),
            "estimated": True
        }

    # Estimate daily cost (24 hours at current power)
    now = dt.datetime.utcnow()
    day_start = now - dt.timedelta(days=1)

    cost_calc = ElectricityCostService.calculate_cost_for_period(
        total_power_w, day_start, now, rate
    )

    daily_cost = cost_calc["energy_cost_usd"] + rate.daily_service_charge_usd
    daily_kwh = cost_calc["total_kwh"]

    # Estimate monthly (30 days)
    monthly_cost = daily_cost * 30
    monthly_kwh = daily_kwh * 30

    return {
        "total_cost_usd": monthly_cost,
        "total_kwh": monthly_kwh,
        "avg_rate_usd_per_kwh": cost_calc["avg_rate_usd_per_kwh"],
        "num_records": 0,
        "tou_breakdown_usd": cost_calc.get("tou_breakdown"),
        "period_start": dt.datetime.utcnow() - dt.timedelta(days=30),
        "period_end": dt.datetime.utcnow(),
        "estimated": True,
        "fleet_power_w": total_power_w,
        "num_miners": len(latest_metrics)
    }


@bp.route("/rates", methods=["GET"])
def get_rates():
    """Get all electricity rate configurations."""
    session = SessionLocal()
    try:
        active_only = request.args.get("active_only", "false").lower() == "true"
        location = request.args.get("location")

        query = session.query(ElectricityRate)

        if active_only:
            query = query.filter(ElectricityRate.active == True)
        if location:
            query = query.filter(ElectricityRate.location == location)

        rates = query.order_by(ElectricityRate.created_at.desc()).all()

        return jsonify({
            "ok": True,
            "rates": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "active": r.active,
                    "rate_type": r.rate_type,
                    "flat_rate_usd_per_kwh": r.flat_rate_usd_per_kwh,
                    "tou_schedule": r.tou_schedule,
                    "tiered_rates": r.tiered_rates,
                    "daily_service_charge_usd": r.daily_service_charge_usd,
                    "demand_charge_usd_per_kw": r.demand_charge_usd_per_kw,
                    "location": r.location,
                    "timezone": r.timezone,
                    "utility_name": r.utility_name,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None
                }
                for r in rates
            ],
            "count": len(rates)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/rates/<int:rate_id>", methods=["GET"])
def get_rate(rate_id: int):
    """Get a specific electricity rate."""
    session = SessionLocal()
    try:
        rate = session.query(ElectricityRate).filter(ElectricityRate.id == rate_id).first()

        if not rate:
            return jsonify({"ok": False, "error": "Rate not found"}), 404

        return jsonify({
            "ok": True,
            "rate": {
                "id": rate.id,
                "name": rate.name,
                "description": rate.description,
                "active": rate.active,
                "rate_type": rate.rate_type,
                "flat_rate_usd_per_kwh": rate.flat_rate_usd_per_kwh,
                "tou_schedule": rate.tou_schedule,
                "tiered_rates": rate.tiered_rates,
                "daily_service_charge_usd": rate.daily_service_charge_usd,
                "demand_charge_usd_per_kw": rate.demand_charge_usd_per_kw,
                "location": rate.location,
                "timezone": rate.timezone,
                "utility_name": rate.utility_name,
                "account_number": rate.account_number,
                "notes": rate.notes,
                "season_start_month": rate.season_start_month,
                "season_end_month": rate.season_end_month,
                "created_at": rate.created_at.isoformat() if rate.created_at else None,
                "updated_at": rate.updated_at.isoformat() if rate.updated_at else None
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/rates", methods=["POST"])
def create_rate():
    """Create a new electricity rate configuration."""
    session = SessionLocal()
    try:
        data = request.json

        # Deactivate other rates for same location if this one is active
        if data.get("active") and data.get("location"):
            session.query(ElectricityRate).filter(
                and_(
                    ElectricityRate.location == data["location"],
                    ElectricityRate.active == True
                )
            ).update({"active": False})

        rate = ElectricityRate(
            name=data["name"],
            description=data.get("description"),
            active=data.get("active", True),
            location=data.get("location"),
            timezone=data.get("timezone", "UTC"),
            rate_type=data.get("rate_type", "flat"),
            flat_rate_usd_per_kwh=data.get("flat_rate_usd_per_kwh"),
            tou_schedule=data.get("tou_schedule"),
            tiered_rates=data.get("tiered_rates"),
            daily_service_charge_usd=data.get("daily_service_charge_usd", 0.0),
            demand_charge_usd_per_kw=data.get("demand_charge_usd_per_kw", 0.0),
            utility_name=data.get("utility_name"),
            account_number=data.get("account_number"),
            notes=data.get("notes"),
            season_start_month=data.get("season_start_month"),
            season_end_month=data.get("season_end_month")
        )

        session.add(rate)
        session.commit()

        return jsonify({
            "ok": True,
            "message": "Electricity rate created",
            "rate_id": rate.id
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/rates/<int:rate_id>", methods=["PUT"])
def update_rate(rate_id: int):
    """Update an existing electricity rate."""
    session = SessionLocal()
    try:
        rate = session.query(ElectricityRate).filter(ElectricityRate.id == rate_id).first()

        if not rate:
            return jsonify({"ok": False, "error": "Rate not found"}), 404

        data = request.json

        # Deactivate other rates if activating this one
        if data.get("active") and not rate.active and rate.location:
            session.query(ElectricityRate).filter(
                and_(
                    ElectricityRate.location == rate.location,
                    ElectricityRate.active == True,
                    ElectricityRate.id != rate_id
                )
            ).update({"active": False})

        # Update fields
        for field in ["name", "description", "active", "location", "timezone", "rate_type",
                      "flat_rate_usd_per_kwh", "tou_schedule", "tiered_rates",
                      "daily_service_charge_usd", "demand_charge_usd_per_kw",
                      "utility_name", "account_number", "notes",
                      "season_start_month", "season_end_month"]:
            if field in data:
                setattr(rate, field, data[field])

        rate.updated_at = dt.datetime.utcnow()
        session.commit()

        return jsonify({
            "ok": True,
            "message": "Electricity rate updated"
        })

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/rates/<int:rate_id>", methods=["DELETE"])
def delete_rate(rate_id: int):
    """Delete an electricity rate."""
    session = SessionLocal()
    try:
        rate = session.query(ElectricityRate).filter(ElectricityRate.id == rate_id).first()

        if not rate:
            return jsonify({"ok": False, "error": "Rate not found"}), 404

        session.delete(rate)
        session.commit()

        return jsonify({
            "ok": True,
            "message": "Electricity rate deleted"
        })

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/rates/<int:rate_id>/activate", methods=["POST"])
def activate_rate(rate_id: int):
    """Activate a specific rate (deactivating others for same location)."""
    session = SessionLocal()
    try:
        rate = session.query(ElectricityRate).filter(ElectricityRate.id == rate_id).first()

        if not rate:
            return jsonify({"ok": False, "error": "Rate not found"}), 404

        # Deactivate other rates for same location
        if rate.location:
            session.query(ElectricityRate).filter(
                and_(
                    ElectricityRate.location == rate.location,
                    ElectricityRate.active == True,
                    ElectricityRate.id != rate_id
                )
            ).update({"active": False})

        rate.active = True
        rate.updated_at = dt.datetime.utcnow()
        session.commit()

        return jsonify({
            "ok": True,
            "message": f"Rate '{rate.name}' activated"
        })

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/costs", methods=["GET"])
def get_costs():
    """Get electricity cost records."""
    session = SessionLocal()
    try:
        # Query parameters
        miner_ip = request.args.get("miner_ip")
        location = request.args.get("location")
        start_date = request.args.get("start_date")  # ISO format
        end_date = request.args.get("end_date")
        limit = int(request.args.get("limit", 100))

        query = session.query(ElectricityCost)

        if miner_ip:
            query = query.filter(ElectricityCost.miner_ip == miner_ip)
        if location:
            query = query.filter(ElectricityCost.location == location)
        if start_date:
            query = query.filter(ElectricityCost.period_start >= dt.datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(ElectricityCost.period_end <= dt.datetime.fromisoformat(end_date))

        costs = query.order_by(ElectricityCost.timestamp.desc()).limit(limit).all()

        return jsonify({
            "ok": True,
            "costs": [
                {
                    "id": c.id,
                    "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                    "miner_ip": c.miner_ip,
                    "location": c.location,
                    "period_start": c.period_start.isoformat() if c.period_start else None,
                    "period_end": c.period_end.isoformat() if c.period_end else None,
                    "duration_hours": c.duration_hours,
                    "total_kwh": c.total_kwh,
                    "avg_power_kw": c.avg_power_kw,
                    "rate_name": c.rate_name,
                    "avg_rate_usd_per_kwh": c.avg_rate_usd_per_kwh,
                    "energy_cost_usd": c.energy_cost_usd,
                    "demand_charge_usd": c.demand_charge_usd,
                    "service_charge_usd": c.service_charge_usd,
                    "total_cost_usd": c.total_cost_usd,
                    "tou_breakdown_usd": c.tou_breakdown_usd
                }
                for c in costs
            ],
            "count": len(costs)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/costs/summary", methods=["GET"])
def get_cost_summary():
    """Get aggregated electricity cost summary."""
    session = SessionLocal()
    try:
        # Query parameters
        miner_ip = request.args.get("miner_ip")
        location = request.args.get("location")
        start_date = request.args.get("start_date")  # ISO format
        end_date = request.args.get("end_date")

        # Default to last 30 days if not specified
        if not end_date:
            end_dt = dt.datetime.utcnow()
        else:
            end_dt = dt.datetime.fromisoformat(end_date)

        if not start_date:
            start_dt = end_dt - dt.timedelta(days=30)
        else:
            start_dt = dt.datetime.fromisoformat(start_date)

        summary = ElectricityCostService.get_cost_summary(
            session, start_dt, end_dt, miner_ip, location
        )

        # If no historical data, estimate based on current fleet power
        if summary["num_records"] == 0:
            summary = estimate_costs_from_fleet(session, location)

        return jsonify({
            "ok": True,
            "summary": summary
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/calculate", methods=["POST"])
def calculate_cost():
    """Calculate electricity cost for given parameters (without storing)."""
    try:
        data = request.json

        power_w = data["power_w"]
        start_time = dt.datetime.fromisoformat(data["start_time"])
        end_time = dt.datetime.fromisoformat(data["end_time"])
        rate_id = data.get("rate_id")
        location = data.get("location")

        session = SessionLocal()

        if rate_id:
            rate = session.query(ElectricityRate).filter(ElectricityRate.id == rate_id).first()
        else:
            rate = ElectricityCostService.get_active_rate(session, location)

        if not rate:
            session.close()
            return jsonify({"ok": False, "error": "No rate specified or active"}), 400

        result = ElectricityCostService.calculate_cost_for_period(
            power_w, start_time, end_time, rate
        )

        session.close()

        return jsonify({
            "ok": True,
            "calculation": result,
            "rate_used": {
                "id": rate.id,
                "name": rate.name,
                "rate_type": rate.rate_type
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/initialize", methods=["POST"])
def initialize_rates():
    """Create default example rate configurations."""
    try:
        rates = create_default_rates()
        return jsonify({
            "ok": True,
            "message": f"Created {len(rates)} default rate configurations",
            "rates": [{"id": r.id, "name": r.name} for r in rates]
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/current-rate", methods=["GET"])
def get_current_rate():
    """Get the currently active rate for a location."""
    session = SessionLocal()
    try:
        location = request.args.get("location")
        timestamp_str = request.args.get("timestamp")  # optional, defaults to now

        if timestamp_str:
            timestamp = dt.datetime.fromisoformat(timestamp_str)
        else:
            timestamp = dt.datetime.utcnow()

        rate = ElectricityCostService.get_active_rate(session, location)

        if not rate:
            return jsonify({
                "ok": False,
                "error": "No active rate found for location"
            }), 404

        current_rate_value = ElectricityCostService.calculate_rate_for_time(rate, timestamp)

        return jsonify({
            "ok": True,
            "rate": {
                "id": rate.id,
                "name": rate.name,
                "rate_type": rate.rate_type,
                "current_rate_usd_per_kwh": current_rate_value,
                "timestamp": timestamp.isoformat()
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/record-costs", methods=["POST"])
def record_costs_now():
    """Manually trigger electricity cost recording for the last hour."""
    session = SessionLocal()
    try:
        # Get all active electricity rates
        active_rates = session.query(ElectricityRate).filter(ElectricityRate.active == True).all()

        if not active_rates:
            return jsonify({
                "ok": False,
                "error": "No active electricity rates configured"
            }), 400

        # Define the recording period (last hour)
        period_end = dt.datetime.utcnow()
        period_start = period_end - dt.timedelta(hours=1)

        # Get all miners
        miners = session.query(Miner).all()

        # Group miners by location for rate matching
        location_groups = {}
        for miner in miners:
            location = miner.location or "default"
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(miner.miner_ip)

        total_recorded = 0
        failed = 0

        # Process each location group
        for location, miner_ips in location_groups.items():
            # Find active rate for this location
            rate = None
            for r in active_rates:
                if r.location == location or (not r.location and location == "default"):
                    rate = r
                    break

            if not rate:
                # Use first active rate as fallback
                rate = active_rates[0]

            # Get average power consumption for each miner in the period
            for miner_ip in miner_ips:
                # Query metrics for this miner in the period
                metrics = session.query(Metric).filter(
                    Metric.miner_ip == miner_ip,
                    Metric.timestamp >= period_start,
                    Metric.timestamp <= period_end
                ).all()

                if not metrics:
                    continue

                # Calculate average power
                avg_power_w = sum(m.power_w for m in metrics if m.power_w) / len(metrics)

                if avg_power_w == 0:
                    continue

                try:
                    # Record the cost for this miner
                    ElectricityCostService.record_cost(
                        session=session,
                        period_start=period_start,
                        period_end=period_end,
                        power_w=avg_power_w,
                        miner_ip=miner_ip,
                        location=location if location != "default" else None,
                        rate=rate
                    )
                    total_recorded += 1
                except Exception as e:
                    failed += 1

        return jsonify({
            "ok": True,
            "message": f"Recorded electricity costs for {total_recorded} miners",
            "total_recorded": total_recorded,
            "failed": failed,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat()
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/trends", methods=["GET"])
def get_cost_trends():
    """Get electricity cost trends over time (daily aggregates)."""
    session = SessionLocal()
    try:
        # Query parameters
        days = int(request.args.get("days", 30))
        miner_ip = request.args.get("miner_ip")
        location = request.args.get("location")

        end_date = dt.datetime.utcnow()
        start_date = end_date - dt.timedelta(days=days)

        # Query all costs in the period
        query = session.query(ElectricityCost).filter(
            and_(
                ElectricityCost.period_start >= start_date,
                ElectricityCost.period_end <= end_date
            )
        )

        if miner_ip:
            query = query.filter(ElectricityCost.miner_ip == miner_ip)
        if location:
            query = query.filter(ElectricityCost.location == location)

        costs = query.order_by(ElectricityCost.period_start).all()

        # Aggregate by day
        daily_costs = {}
        for cost in costs:
            day = cost.period_start.date().isoformat()
            if day not in daily_costs:
                daily_costs[day] = {
                    "date": day,
                    "total_cost_usd": 0.0,
                    "total_kwh": 0.0,
                    "num_records": 0
                }
            daily_costs[day]["total_cost_usd"] += cost.total_cost_usd
            daily_costs[day]["total_kwh"] += cost.total_kwh
            daily_costs[day]["num_records"] += 1

        # Convert to sorted list
        trend_data = sorted(daily_costs.values(), key=lambda x: x["date"])

        # Calculate averages
        if trend_data:
            avg_daily_cost = sum(d["total_cost_usd"] for d in trend_data) / len(trend_data)
            avg_daily_kwh = sum(d["total_kwh"] for d in trend_data) / len(trend_data)
        else:
            avg_daily_cost = 0.0
            avg_daily_kwh = 0.0

        return jsonify({
            "ok": True,
            "trends": trend_data,
            "summary": {
                "avg_daily_cost_usd": avg_daily_cost,
                "avg_daily_kwh": avg_daily_kwh,
                "total_days": len(trend_data),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat()
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


# ============================================================================
# HTML PAGE ROUTE
# ============================================================================

@bp.route('/page', methods=['GET'])
def electricity_page():
    """Render the electricity cost tracking dashboard HTML page."""
    return render_template('electricity.html')
