# Electricity Cost Tracking System

## Overview

The electricity cost tracking system automatically records and analyzes electricity costs for your mining fleet based on actual power consumption and configurable rate plans.

## Features

### 1. **Flexible Rate Configurations**
- **Flat Rate**: Simple 24/7 pricing (e.g., $0.12/kWh)
- **Time-of-Use (TOU)**: Different rates for different times of day and days of week
  - Peak hours (highest rates)
  - Off-peak hours (lowest rates)
  - Shoulder periods (mid-range rates)
  - Weekend rates
- **Service Charges**: Daily fixed charges
- **Demand Charges**: Per-kW demand fees ($/kW)

### 2. **Automatic Cost Recording**
The scheduler automatically records electricity costs every hour:
- Calculates average power consumption per miner from metrics
- Applies the appropriate rate (location-based)
- Stores detailed cost records in the database
- Supports multiple locations with different rates

### 3. **Real-Time Cost Estimation**
When no historical data exists, the system estimates costs based on:
- Current fleet power consumption
- Active electricity rates
- Projected daily and monthly costs

### 4. **Historical Trends**
- View cost trends over time
- Daily cost aggregation
- Compare costs across different periods
- Analyze cost patterns

## Usage

### Setting Up Rates

1. **Navigate to the Electricity page**: `http://localhost:5000/dashboard/electricity`

2. **Create a new rate**:
   - Click "➕ Create New Rate"
   - Choose rate type (Flat or Time-of-Use)
   - Enter rate details
   - Set location (optional, for multi-location setups)
   - Mark as active

3. **Initialize default rates** (optional):
   - Click "🔄 Initialize Default Rates"
   - Creates example flat and TOU rates for testing

### Recording Costs

#### Automatic Recording (Recommended)
The scheduler automatically records costs every hour. No action needed!

#### Manual Recording
Click "💾 Record Costs Now" to immediately record costs for the last hour.

### Viewing Cost Data

#### Summary Cards
- **Active Rates**: Number of active rate configurations
- **Current Rate**: Current electricity rate ($/kWh)
- **Est. Daily Cost**: Estimated daily electricity cost
- **Monthly Est.**: Projected monthly cost

#### Historical Summary (Last 30 Days)
- Total cost
- Total kWh consumed
- Average rate
- Number of records

## API Endpoints

### Rate Management
- `GET /api/electricity/rates` - List all rates
- `POST /api/electricity/rates` - Create new rate
- `PUT /api/electricity/rates/<id>` - Update rate
- `DELETE /api/electricity/rates/<id>` - Delete rate
- `POST /api/electricity/rates/<id>/activate` - Activate rate

### Cost Data
- `GET /api/electricity/costs` - Get cost records
- `GET /api/electricity/costs/summary` - Get cost summary
- `POST /api/electricity/record-costs` - Manually record costs
- `GET /api/electricity/trends` - Get daily cost trends

### Utilities
- `POST /api/electricity/initialize` - Create default rates
- `GET /api/electricity/current-rate` - Get current rate for location
- `POST /api/electricity/calculate` - Calculate cost without saving

## Database Schema

### ElectricityRate
Stores rate configurations:
- `name`, `description`
- `rate_type`: "flat" or "tou"
- `flat_rate_usd_per_kwh`: Flat rate value
- `tou_schedule`: JSON array of TOU periods
- `daily_service_charge_usd`: Fixed daily charge
- `demand_charge_usd_per_kw`: Demand charge
- `location`: Location identifier
- `active`: Boolean flag

### ElectricityCost
Stores actual cost records:
- `miner_ip`, `location`
- `period_start`, `period_end`
- `total_kwh`: Energy consumed
- `avg_power_kw`: Average power
- `rate_name`: Rate used for calculation
- `avg_rate_usd_per_kwh`: Average rate applied
- `energy_cost_usd`: Energy cost
- `total_cost_usd`: Total cost including charges
- `tou_breakdown_usd`: JSON breakdown by TOU period

## Scheduler Job

The `record_electricity_costs()` job runs every hour:
1. Checks for active electricity rates
2. Groups miners by location
3. Queries metrics from the last hour
4. Calculates average power per miner
5. Records cost using appropriate rate
6. Logs results

## Example TOU Schedule

```json
[
  {
    "name": "Off-Peak",
    "rate": 0.08,
    "days": [0, 1, 2, 3, 4, 5, 6],
    "start_hour": 21,
    "end_hour": 7
  },
  {
    "name": "Peak",
    "rate": 0.22,
    "days": [0, 1, 2, 3, 4],
    "start_hour": 17,
    "end_hour": 21
  }
]
```

Days: Monday=0, Tuesday=1, ..., Sunday=6

## Tips

1. **Multiple Locations**: Create separate rates for each location and set the `location` field
2. **Seasonal Rates**: Create different rate configurations for summer/winter
3. **Testing**: Use "Record Costs Now" to immediately see results
4. **Historical Data**: Let the system run for a few days to build up historical trends
5. **Rate Changes**: When changing rates, the old rate remains in historical records

## Troubleshooting

### No cost data showing
- Ensure at least one rate is marked as "Active"
- Check that miners are reporting metrics
- Manually trigger "Record Costs Now" to create initial data

### Costs seem incorrect
- Verify the active rate configuration
- Check miner power consumption in metrics
- Review the rate type (flat vs TOU)

### Multiple active rates
- Only one rate per location should be active
- System automatically deactivates others when activating a rate

## Future Enhancements

Potential improvements:
- Cost forecasting based on historical patterns
- Budget alerts and thresholds
- Cost optimization recommendations
- Integration with actual utility bills
- Export cost reports (CSV, PDF)
- Graphical trend visualization
- Per-miner cost breakdown
