# Electricity Cost Tracking System

## Overview

The Electricity Cost Tracking system provides comprehensive management of electricity rates and cost calculations for your mining operation. It supports multiple rate structures including flat rates, time-of-use (TOU) pricing, and tiered billing.

## Features

### ✅ Rate Management
- **Multiple Rate Configurations**: Create and manage different electricity rate plans
- **Flat Rate Billing**: Simple $/kWh pricing structure
- **Time-of-Use (TOU) Rates**: Different rates for different times of day and days of week
- **Tiered Pricing**: Volume-based pricing tiers (planned)
- **Location-Based Rates**: Different rates for different physical locations/facilities

### ✅ Cost Calculation
- **Real-time Cost Calculation**: Calculate electricity costs for any time period
- **TOU Cost Breakdown**: Detailed breakdown by rate period (peak/off-peak/shoulder)
- **Historical Cost Tracking**: Time-series cost records
- **Daily/Monthly Estimates**: Project costs based on consumption patterns

### ✅ Additional Charges
- **Service Charges**: Daily connection fees
- **Demand Charges**: Peak demand-based charges ($/kW)
- **Seasonal Rates**: Support for summer/winter rate schedules

## Database Models

### ElectricityRate
Stores electricity rate configuration:

```python
{
    "id": 1,
    "name": "Summer TOU 2024",
    "description": "Time-of-use rates for summer season",
    "active": true,
    "rate_type": "tou",  # 'flat', 'tou', or 'tiered'
    "location": "Main Facility",
    "timezone": "America/New_York",
    
    # Flat rate
    "flat_rate_usd_per_kwh": 0.12,
    
    # Time-of-use schedule
    "tou_schedule": [
        {
            "name": "Off-Peak",
            "rate": 0.08,
            "days": [0,1,2,3,4,5,6],  # Mon=0, Sun=6
            "start_hour": 21,
            "end_hour": 7
        },
        {
            "name": "Peak",
            "rate": 0.22,
            "days": [0,1,2,3,4],  # Weekdays
            "start_hour": 17,
            "end_hour": 21
        }
    ],
    
    # Additional charges
    "daily_service_charge_usd": 1.00,
    "demand_charge_usd_per_kw": 5.00,
    
    # Utility info
    "utility_name": "Example Electric Co.",
    "account_number": "123456789"
}
```

### ElectricityCost
Time-series cost records:

```python
{
    "id": 1,
    "timestamp": "2024-01-15T12:00:00Z",
    "miner_ip": "10.0.0.100",  # or null for fleet-wide
    "location": "Main Facility",
    
    # Time period
    "period_start": "2024-01-15T00:00:00Z",
    "period_end": "2024-01-16T00:00:00Z",
    "duration_hours": 24.0,
    
    # Consumption
    "total_kwh": 72.0,
    "avg_power_kw": 3.0,
    "peak_power_kw": 3.2,
    
    # Rate info
    "rate_id": 1,
    "rate_name": "Summer TOU 2024",
    "avg_rate_usd_per_kwh": 0.1125,
    
    # Cost breakdown
    "energy_cost_usd": 8.10,
    "demand_charge_usd": 0.00,
    "service_charge_usd": 1.00,
    "total_cost_usd": 9.10,
    
    # TOU breakdown (optional)
    "tou_breakdown_usd": {
        "Off-Peak": 3.20,
        "Shoulder": 2.88,
        "Peak": 2.02
    }
}
```

## API Endpoints

### Rate Management

#### GET /api/electricity/rates
Get all electricity rate configurations.

**Query Parameters:**
- `active_only` (boolean): Only return active rates
- `location` (string): Filter by location

**Response:**
```json
{
    "ok": true,
    "rates": [...],
    "count": 2
}
```

#### GET /api/electricity/rates/{id}
Get a specific rate configuration.

#### POST /api/electricity/rates
Create a new rate configuration.

**Request Body:**
```json
{
    "name": "Winter TOU 2024",
    "description": "Time-of-use rates for winter",
    "active": true,
    "rate_type": "tou",
    "location": "Main Facility",
    "timezone": "America/New_York",
    "flat_rate_usd_per_kwh": 0.10,
    "tou_schedule": [...],
    "daily_service_charge_usd": 0.50,
    "demand_charge_usd_per_kw": 0.00
}
```

#### PUT /api/electricity/rates/{id}
Update an existing rate.

#### DELETE /api/electricity/rates/{id}
Delete a rate configuration.

#### POST /api/electricity/rates/{id}/activate
Activate a rate (deactivates others for same location).

### Cost Queries

#### GET /api/electricity/costs
Get electricity cost records.

**Query Parameters:**
- `miner_ip`: Filter by miner
- `location`: Filter by location
- `start_date`: ISO format start date
- `end_date`: ISO format end date
- `limit`: Max records to return (default: 100)

#### GET /api/electricity/costs/summary
Get aggregated cost summary.

**Query Parameters:**
- `miner_ip`: Filter by miner
- `location`: Filter by location
- `start_date`: ISO format (default: 30 days ago)
- `end_date`: ISO format (default: now)

**Response:**
```json
{
    "ok": true,
    "summary": {
        "total_cost_usd": 273.50,
        "total_kwh": 2160.0,
        "avg_rate_usd_per_kwh": 0.1266,
        "num_records": 30,
        "tou_breakdown_usd": {
            "Off-Peak": 120.00,
            "Shoulder": 85.50,
            "Peak": 68.00
        },
        "period_start": "2024-01-01T00:00:00Z",
        "period_end": "2024-01-31T00:00:00Z"
    }
}
```

### Utilities

#### POST /api/electricity/calculate
Calculate cost for given parameters (without storing).

**Request Body:**
```json
{
    "power_w": 3000,
    "start_time": "2024-01-15T00:00:00Z",
    "end_time": "2024-01-16T00:00:00Z",
    "rate_id": 1,
    "location": "Main Facility"
}
```

**Response:**
```json
{
    "ok": true,
    "calculation": {
        "total_kwh": 72.0,
        "energy_cost_usd": 8.10,
        "avg_rate_usd_per_kwh": 0.1125,
        "tou_breakdown": {...}
    },
    "rate_used": {
        "id": 1,
        "name": "Summer TOU 2024",
        "rate_type": "tou"
    }
}
```

#### POST /api/electricity/initialize
Create default example rate configurations.

#### GET /api/electricity/current-rate
Get the currently active rate for a location.

**Query Parameters:**
- `location`: Location name (optional)
- `timestamp`: ISO format timestamp (optional, defaults to now)

## Usage Examples

### Python Integration

```python
from core.electricity import ElectricityCostService
from core.db import SessionLocal, ElectricityRate
import datetime as dt

# Get active rate
session = SessionLocal()
rate = ElectricityCostService.get_active_rate(session, location="Main Facility")

# Calculate cost for a period
cost_data = ElectricityCostService.calculate_cost_for_period(
    power_w=3000,  # 3kW
    start_time=dt.datetime(2024, 1, 15, 0, 0),
    end_time=dt.datetime(2024, 1, 16, 0, 0),
    rate=rate
)
print(f"Total cost: ${cost_data['energy_cost_usd']:.2f}")
print(f"Total kWh: {cost_data['total_kwh']:.2f}")
print(f"Avg rate: ${cost_data['avg_rate_usd_per_kwh']:.4f}/kWh")

# Record cost
cost_record = ElectricityCostService.record_cost(
    session=session,
    period_start=dt.datetime(2024, 1, 15, 0, 0),
    period_end=dt.datetime(2024, 1, 16, 0, 0),
    power_w=3000,
    miner_ip="10.0.0.100",
    location="Main Facility"
)

# Get cost summary
summary = ElectricityCostService.get_cost_summary(
    session=session,
    start_date=dt.datetime(2024, 1, 1),
    end_date=dt.datetime(2024, 1, 31),
    location="Main Facility"
)
print(f"Monthly cost: ${summary['total_cost_usd']:.2f}")
```

### JavaScript/Frontend Integration

```javascript
// Get all rates
const rates = await fetch('/api/electricity/rates').then(r => r.json());

// Create new TOU rate
const newRate = await fetch('/api/electricity/rates', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        name: "Summer TOU 2024",
        rate_type: "tou",
        active: true,
        tou_schedule: [
            {
                name: "Off-Peak",
                rate: 0.08,
                days: [0,1,2,3,4,5,6],
                start_hour: 0,
                end_hour: 7
            }
        ]
    })
}).then(r => r.json());

// Calculate cost
const calculation = await fetch('/api/electricity/calculate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        power_w: 3000,
        start_time: "2024-01-15T00:00:00Z",
        end_time: "2024-01-16T00:00:00Z",
        rate_id: 1
    })
}).then(r => r.json());

console.log(`Cost: $${calculation.calculation.energy_cost_usd.toFixed(2)}`);
```

## Web Interface

Access the Electricity Management dashboard at:
```
http://your-server:5000/dashboard/electricity
```

### Features:
- **Rate Configuration**: Create, edit, and manage electricity rates
- **Visual Rate Display**: See all configured rates with clear visual indicators
- **TOU Schedule Builder**: Easy-to-use interface for creating time-of-use schedules
- **Cost Summary**: View historical costs with breakdown by rate period
- **Quick Actions**: Initialize default rates, activate/deactivate rates
- **Cost Estimates**: See daily and monthly cost projections

## Time-of-Use (TOU) Rate Examples

### Residential TOU (Simple)
```json
{
    "tou_schedule": [
        {
            "name": "Off-Peak",
            "rate": 0.08,
            "days": [0,1,2,3,4,5,6],
            "start_hour": 21,
            "end_hour": 7
        },
        {
            "name": "Peak",
            "rate": 0.18,
            "days": [0,1,2,3,4,5,6],
            "start_hour": 7,
            "end_hour": 21
        }
    ]
}
```

### Commercial TOU (Advanced)
```json
{
    "tou_schedule": [
        {
            "name": "Super Off-Peak",
            "rate": 0.06,
            "days": [0,1,2,3,4,5,6],
            "start_hour": 0,
            "end_hour": 6
        },
        {
            "name": "Off-Peak",
            "rate": 0.10,
            "days": [0,1,2,3,4],
            "start_hour": 6,
            "end_hour": 9
        },
        {
            "name": "Mid-Peak",
            "rate": 0.14,
            "days": [0,1,2,3,4],
            "start_hour": 9,
            "end_hour": 17
        },
        {
            "name": "On-Peak",
            "rate": 0.22,
            "days": [0,1,2,3,4],
            "start_hour": 17,
            "end_hour": 21
        },
        {
            "name": "Evening Off-Peak",
            "rate": 0.10,
            "days": [0,1,2,3,4],
            "start_hour": 21,
            "end_hour": 24
        },
        {
            "name": "Weekend",
            "rate": 0.08,
            "days": [5,6],
            "start_hour": 6,
            "end_hour": 24
        }
    ]
}
```

## Integration with Profitability Tracking

The electricity cost system integrates seamlessly with the existing profitability tracking:

```python
# In profitability calculations, use electricity cost data
from core.electricity import ElectricityCostService

# Get actual electricity cost for a miner/period
cost_summary = ElectricityCostService.get_cost_summary(
    session,
    start_date,
    end_date,
    miner_ip=miner.ip
)

# Use in profitability calculation
daily_revenue_usd = btc_per_day * btc_price_usd
daily_electricity_cost = cost_summary['total_cost_usd'] / days_in_period
daily_profit = daily_revenue_usd - daily_electricity_cost
profit_margin = (daily_profit / daily_revenue_usd) * 100
```

## Best Practices

### 1. Rate Configuration
- Create separate rate configurations for different seasons
- Use descriptive names (e.g., "Summer TOU 2024", "Winter Flat Rate")
- Only have one active rate per location at a time
- Document your utility bill structure in the description field

### 2. TOU Schedule Design
- Ensure all hours are covered (0-24)
- Account for weekend vs. weekday differences
- Test calculations before activating
- Update rates when utility changes pricing

### 3. Cost Tracking
- Record costs regularly (daily or per billing cycle)
- Include location information for multi-site operations
- Review TOU breakdowns to optimize operation schedules
- Compare estimated vs. actual utility bills

### 4. Optimization Opportunities
- **Load Shifting**: Run miners during off-peak hours if possible
- **Demand Management**: Reduce peak power to minimize demand charges
- **Seasonal Planning**: Adjust operations based on seasonal rate changes
- **Cost Forecasting**: Use historical data to predict future costs

## Troubleshooting

### Issue: No active rate found
**Solution**: Navigate to `/dashboard/electricity` and either create a new rate or activate an existing one.

### Issue: TOU breakdown showing unexpected costs
**Solution**: Verify the TOU schedule covers all hours and days. Check that `start_hour` and `end_hour` values are correct.

### Issue: Costs seem incorrect
**Solution**: 
1. Verify the power consumption (watts) is accurate
2. Check the rate values ($/kWh)
3. Ensure timezone is set correctly
4. Review service and demand charges

## Future Enhancements

Planned features for future releases:

- [ ] Tiered pricing support (volume-based rates)
- [ ] Real-time demand charge calculation
- [ ] Cost optimization recommendations
- [ ] Automated scheduler integration (run during cheap hours)
- [ ] Utility bill upload and reconciliation
- [ ] Carbon intensity tracking
- [ ] Multi-currency support
- [ ] Rate comparison tools
- [ ] Export cost reports (PDF/CSV)
- [ ] Email alerts for high-cost periods

## Support

For questions or issues with the electricity cost tracking system:
1. Check this documentation
2. Review API endpoint responses for error messages
3. Check application logs in `logs/` directory
4. Verify database connectivity
5. Ensure rate configurations are valid

## Database Schema

Initialize the electricity tracking tables by running the application. The tables will be created automatically:

```bash
python main.py
```

Or manually initialize:
```python
from core.db import init_db
init_db()
```

To create example rates:
```bash
curl -X POST http://localhost:5000/api/electricity/initialize
```

---

**Version**: 1.0  
**Last Updated**: 2025-10-19  
**Author**: Mining Operations Team
