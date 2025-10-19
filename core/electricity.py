"""
Electricity cost tracking and calculation engine.

Supports:
- Simple flat-rate billing
- Time-of-use (TOU) rate schedules
- Peak/off-peak/shoulder pricing
- Daily, weekly, and monthly cost aggregation
- Cost forecasting
"""

from __future__ import annotations
import datetime as dt
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from core.db import SessionLocal, ElectricityRate, ElectricityCost


class ElectricityCostService:
    """Service for calculating and tracking electricity costs."""

    @staticmethod
    def get_active_rate(session: Session, location: str = None) -> Optional[ElectricityRate]:
        """Get the currently active electricity rate for a location."""
        query = session.query(ElectricityRate).filter(ElectricityRate.active == True)

        if location:
            query = query.filter(ElectricityRate.location == location)

        # Get the most recently created active rate
        rate = query.order_by(ElectricityRate.created_at.desc()).first()
        return rate

    @staticmethod
    def calculate_rate_for_time(rate: ElectricityRate, timestamp: dt.datetime) -> float:
        """Calculate the rate ($/kWh) for a specific timestamp based on rate configuration."""
        if rate.rate_type == "flat":
            return rate.flat_rate_usd_per_kwh or 0.0

        elif rate.rate_type == "tou" and rate.tou_schedule:
            # Find matching TOU period
            weekday = timestamp.weekday()  # Monday=0, Sunday=6
            hour = timestamp.hour

            for period in rate.tou_schedule:
                if weekday in period.get("days", []):
                    start_h = period.get("start_hour", 0)
                    end_h = period.get("end_hour", 24)

                    # Handle periods that wrap around midnight
                    if start_h <= end_h:
                        if start_h <= hour < end_h:
                            return period.get("rate", 0.0)
                    else:
                        if hour >= start_h or hour < end_h:
                            return period.get("rate", 0.0)

            # If no period matched, return flat rate as fallback
            return rate.flat_rate_usd_per_kwh or 0.0

        else:
            return rate.flat_rate_usd_per_kwh or 0.0

    @staticmethod
    def calculate_cost_for_period(
            power_w: float,
            start_time: dt.datetime,
            end_time: dt.datetime,
            rate: ElectricityRate
    ) -> Dict:
        """
        Calculate electricity cost for a period of constant power consumption.
        
        Returns:
            Dict with keys: total_kwh, total_cost_usd, avg_rate_usd_per_kwh, tou_breakdown
        """
        duration_hours = (end_time - start_time).total_seconds() / 3600
        power_kw = power_w / 1000.0
        total_kwh = power_kw * duration_hours

        if rate.rate_type == "flat":
            rate_value = rate.flat_rate_usd_per_kwh or 0.0
            energy_cost = total_kwh * rate_value
            return {
                "total_kwh": total_kwh,
                "energy_cost_usd": energy_cost,
                "avg_rate_usd_per_kwh": rate_value,
                "tou_breakdown": None
            }

        elif rate.rate_type == "tou" and rate.tou_schedule:
            # Calculate hourly costs for TOU
            tou_breakdown = {}
            total_cost = 0.0
            current = start_time

            while current < end_time:
                next_hour = current + dt.timedelta(hours=1)
                if next_hour > end_time:
                    next_hour = end_time

                hour_duration = (next_hour - current).total_seconds() / 3600
                hour_kwh = power_kw * hour_duration
                hour_rate = ElectricityCostService.calculate_rate_for_time(rate, current)
                hour_cost = hour_kwh * hour_rate

                # Find period name for breakdown
                weekday = current.weekday()
                hour = current.hour
                period_name = "Unknown"

                for period in rate.tou_schedule:
                    if weekday in period.get("days", []):
                        start_h = period.get("start_hour", 0)
                        end_h = period.get("end_hour", 24)
                        if start_h <= end_h:
                            if start_h <= hour < end_h:
                                period_name = period.get("name", "Unknown")
                                break
                        else:
                            if hour >= start_h or hour < end_h:
                                period_name = period.get("name", "Unknown")
                                break

                tou_breakdown[period_name] = tou_breakdown.get(period_name, 0.0) + hour_cost
                total_cost += hour_cost
                current = next_hour

            avg_rate = total_cost / total_kwh if total_kwh > 0 else 0.0

            return {
                "total_kwh": total_kwh,
                "energy_cost_usd": total_cost,
                "avg_rate_usd_per_kwh": avg_rate,
                "tou_breakdown": tou_breakdown
            }

        else:
            # Fallback to flat rate
            rate_value = rate.flat_rate_usd_per_kwh or 0.0
            energy_cost = total_kwh * rate_value
            return {
                "total_kwh": total_kwh,
                "energy_cost_usd": energy_cost,
                "avg_rate_usd_per_kwh": rate_value,
                "tou_breakdown": None
            }

    @staticmethod
    def record_cost(
            session: Session,
            period_start: dt.datetime,
            period_end: dt.datetime,
            power_w: float,
            miner_ip: str = None,
            location: str = None,
            rate: ElectricityRate = None
    ) -> ElectricityCost:
        """Record electricity cost for a time period."""
        if not rate:
            rate = ElectricityCostService.get_active_rate(session, location)
            if not rate:
                raise ValueError("No active electricity rate found")

        # Calculate costs
        cost_data = ElectricityCostService.calculate_cost_for_period(
            power_w, period_start, period_end, rate
        )

        duration_hours = (period_end - period_start).total_seconds() / 3600

        # Create cost record
        cost_record = ElectricityCost(
            timestamp=dt.datetime.utcnow(),
            miner_ip=miner_ip,
            location=location,
            period_start=period_start,
            period_end=period_end,
            duration_hours=duration_hours,
            total_kwh=cost_data["total_kwh"],
            avg_power_kw=power_w / 1000.0,
            rate_id=rate.id,
            rate_name=rate.name,
            avg_rate_usd_per_kwh=cost_data["avg_rate_usd_per_kwh"],
            energy_cost_usd=cost_data["energy_cost_usd"],
            demand_charge_usd=0.0,  # TODO: implement demand charges
            service_charge_usd=rate.daily_service_charge_usd * (duration_hours / 24.0),
            total_cost_usd=cost_data["energy_cost_usd"] + (rate.daily_service_charge_usd * (duration_hours / 24.0)),
            tou_breakdown_usd=cost_data["tou_breakdown"]
        )

        session.add(cost_record)
        session.commit()
        return cost_record

    @staticmethod
    def get_daily_cost(
            session: Session,
            date: dt.date,
            miner_ip: str = None,
            location: str = None
    ) -> float:
        """Get total electricity cost for a specific day."""
        start = dt.datetime.combine(date, dt.time.min)
        end = dt.datetime.combine(date, dt.time.max)

        query = session.query(ElectricityCost).filter(
            and_(
                ElectricityCost.period_start >= start,
                ElectricityCost.period_end <= end
            )
        )

        if miner_ip:
            query = query.filter(ElectricityCost.miner_ip == miner_ip)
        if location:
            query = query.filter(ElectricityCost.location == location)

        costs = query.all()
        return sum(c.total_cost_usd for c in costs)

    @staticmethod
    def get_cost_summary(
            session: Session,
            start_date: dt.datetime,
            end_date: dt.datetime,
            miner_ip: str = None,
            location: str = None
    ) -> Dict:
        """Get cost summary for a date range."""
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

        costs = query.all()

        total_cost = sum(c.total_cost_usd for c in costs)
        total_kwh = sum(c.total_kwh for c in costs)
        avg_rate = total_cost / total_kwh if total_kwh > 0 else 0.0

        # TOU breakdown
        tou_totals = {}
        for cost in costs:
            if cost.tou_breakdown_usd:
                for period, amount in cost.tou_breakdown_usd.items():
                    tou_totals[period] = tou_totals.get(period, 0.0) + amount

        return {
            "total_cost_usd": total_cost,
            "total_kwh": total_kwh,
            "avg_rate_usd_per_kwh": avg_rate,
            "num_records": len(costs),
            "tou_breakdown_usd": tou_totals if tou_totals else None,
            "period_start": start_date,
            "period_end": end_date
        }


def create_default_rates():
    """Create example electricity rate configurations."""
    session = SessionLocal()
    try:
        # Example 1: Simple flat rate
        flat_rate = ElectricityRate(
            name="Flat Rate - Residential",
            description="Simple flat rate, 24/7",
            active=False,
            rate_type="flat",
            flat_rate_usd_per_kwh=0.12,
            daily_service_charge_usd=0.50,
            utility_name="Example Electric Co.",
            timezone="America/New_York"
        )

        # Example 2: Time-of-use (TOU) with peak/off-peak
        tou_rate = ElectricityRate(
            name="TOU - Summer 2024",
            description="Time-of-use rates with peak pricing weekdays 5-9pm",
            active=True,
            rate_type="tou",
            flat_rate_usd_per_kwh=0.12,  # fallback
            tou_schedule=[
                {
                    "name": "Off-Peak",
                    "rate": 0.08,
                    "days": [0, 1, 2, 3, 4, 5, 6],  # All days
                    "start_hour": 21,
                    "end_hour": 7
                },
                {
                    "name": "Shoulder",
                    "rate": 0.12,
                    "days": [0, 1, 2, 3, 4],  # Weekdays
                    "start_hour": 7,
                    "end_hour": 17
                },
                {
                    "name": "Peak",
                    "rate": 0.22,
                    "days": [0, 1, 2, 3, 4],  # Weekdays
                    "start_hour": 17,
                    "end_hour": 21
                },
                {
                    "name": "Weekend",
                    "rate": 0.09,
                    "days": [5, 6],  # Sat, Sun
                    "start_hour": 7,
                    "end_hour": 21
                }
            ],
            daily_service_charge_usd=1.00,
            demand_charge_usd_per_kw=5.00,
            utility_name="Example Electric Co.",
            timezone="America/New_York",
            season_start_month=5,  # May
            season_end_month=9  # September
        )

        session.add(flat_rate)
        session.add(tou_rate)
        session.commit()

        print("✓ Created default electricity rates")
        return [flat_rate, tou_rate]

    except Exception as e:
        session.rollback()
        print(f"Error creating default rates: {e}")
        return []
    finally:
        session.close()
