"""
API endpoints for electricity cost tracking and management.
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import and_, func
from core.db import SessionLocal, ElectricityRate, ElectricityCost
from core.electricity import ElectricityCostService, create_default_rates
import datetime as dt

bp = Blueprint("electricity_api", __name__, url_prefix="/api/electricity")


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
