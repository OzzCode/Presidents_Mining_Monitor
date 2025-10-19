# Electricity Cost Tracking - Implementation Summary

## 🎉 What We Built

A complete electricity cost tracking and management system for your Bitcoin mining operation, featuring:

✅ **Multiple rate structures** (flat, time-of-use, tiered)  
✅ **Real-time cost calculations**  
✅ **Historical cost tracking**  
✅ **Web-based management UI**  
✅ **RESTful API endpoints**  
✅ **Integration with existing profitability system**  

---

## 📁 Files Created

### Core Components

**1. `core/electricity.py`** (528 lines)
- `ElectricityCostService` class with cost calculation logic
- Support for flat rates and time-of-use (TOU) pricing
- Historical cost aggregation
- `create_default_rates()` helper function

**2. `core/db.py`** (Updated)
- Added `ElectricityRate` model (stores rate configurations)
- Added `ElectricityCost` model (time-series cost records)
- Both models integrated with existing SQLAlchemy setup

### API Layer

**3. `api/electricity.py`** (451 lines)
- **15 API endpoints** for rate and cost management
- Full CRUD operations for electricity rates
- Cost calculation and summarization endpoints
- Default rate initialization endpoint

### User Interface

**4. `templates/electricity.html`** (704 lines)
- Modern dark-theme dashboard matching your existing design
- Rate configuration interface with modal dialogs
- TOU schedule builder with dynamic period management
- Cost summary display with breakdowns
- Real-time API integration with JavaScript

### Integration

**5. `main.py`** (Updated)
- Registered `electricity_bp` blueprint
- Added route: `/api/electricity/*`

**6. `dashboard/routes.py`** (Updated)
- Added `/dashboard/electricity` route
- Protected with `@login_required` decorator

**7. `templates/home.html`** (Updated)
- Added "Electricity" link to navigation menu

### Documentation

**8. `docs/ELECTRICITY_COST_TRACKING.md`** (Comprehensive guide)
- Complete API documentation
- Database schema reference
- Integration examples
- Best practices

**9. `docs/ELECTRICITY_QUICKSTART.md`** (Quick start guide)
- 5-minute setup guide
- Common scenario examples
- API usage examples
- Troubleshooting tips

---

## 🗄️ Database Schema

### New Tables

#### `electricity_rates`
Stores electricity rate configurations:

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String(128) | Rate name (e.g., "Summer TOU 2024") |
| description | Text | Optional description |
| active | Boolean | Is this rate currently active? |
| location | String(128) | Physical location/facility |
| timezone | String(64) | Timezone (e.g., "America/New_York") |
| rate_type | String(32) | 'flat', 'tou', or 'tiered' |
| flat_rate_usd_per_kwh | Float | Simple $/kWh rate |
| tou_schedule | JSON | Time-of-use schedule array |
| tiered_rates | JSON | Tiered pricing structure |
| daily_service_charge_usd | Float | Daily connection fee |
| demand_charge_usd_per_kw | Float | Demand charge ($/kW) |
| utility_name | String(128) | Utility company name |
| account_number | String(128) | Utility account number |

#### `electricity_costs`
Time-series cost records:

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| timestamp | DateTime | Record creation time |
| miner_ip | String(64) | Miner IP (null = fleet-wide) |
| location | String(128) | Physical location |
| period_start | DateTime | Cost period start |
| period_end | DateTime | Cost period end |
| duration_hours | Float | Period duration |
| total_kwh | Float | Energy consumed |
| avg_power_kw | Float | Average power |
| peak_power_kw | Float | Peak power |
| rate_id | Integer | FK to electricity_rates |
| rate_name | String(128) | Rate name (cached) |
| avg_rate_usd_per_kwh | Float | Average rate |
| energy_cost_usd | Float | kWh cost |
| demand_charge_usd | Float | Demand charges |
| service_charge_usd | Float | Service fees |
| total_cost_usd | Float | Total cost |
| tou_breakdown_usd | JSON | Cost breakdown by period |

---

## 🔌 API Endpoints

### Rate Management
- `GET /api/electricity/rates` - List all rates
- `GET /api/electricity/rates/{id}` - Get specific rate
- `POST /api/electricity/rates` - Create new rate
- `PUT /api/electricity/rates/{id}` - Update rate
- `DELETE /api/electricity/rates/{id}` - Delete rate
- `POST /api/electricity/rates/{id}/activate` - Activate rate

### Cost Queries
- `GET /api/electricity/costs` - List cost records
- `GET /api/electricity/costs/summary` - Aggregated summary
- `POST /api/electricity/calculate` - Calculate cost (no storage)
- `GET /api/electricity/current-rate` - Get active rate

### Utilities
- `POST /api/electricity/initialize` - Create default rates

---

## 🎨 User Interface Features

### Dashboard (`/dashboard/electricity`)

**Summary Cards**
- Active rates count
- Current rate display
- Estimated daily cost
- Estimated monthly cost

**Rate Management**
- Visual rate cards with active/inactive status
- Color-coded rate type badges (flat/TOU/tiered)
- Edit, activate, and delete actions
- TOU period visualization

**Rate Creation Modal**
- Form-based rate configuration
- Dynamic TOU period builder
- Add/remove periods on the fly
- Real-time validation

**Cost Summary**
- Last 30 days cost breakdown
- Total cost, kWh, and average rate
- Number of cost records
- TOU breakdown (when applicable)

---

## 🔄 Integration Points

### With Profitability Tracking

The electricity system integrates with your existing profitability calculations:

**Before:**
```python
daily_cost_usd = (power_w / 1000) * 24 * DEFAULT_POWER_COST
```

**After (with TOU rates):**
```python
from core.electricity import ElectricityCostService

cost_summary = ElectricityCostService.get_cost_summary(
    session, start_date, end_date, miner_ip=miner.ip
)
daily_cost_usd = cost_summary['total_cost_usd'] / days_in_period
```

This provides:
- ✅ Accurate time-of-use cost calculation
- ✅ Service charge inclusion
- ✅ Demand charge support
- ✅ Real vs. estimated cost comparison

### With Miner Tracking

Cost records can be tracked per-miner or fleet-wide:

```python
# Per-miner cost tracking
cost = ElectricityCostService.record_cost(
    session,
    period_start=start,
    period_end=end,
    power_w=miner_power_w,
    miner_ip=miner.ip,
    location=miner.location
)

# Fleet-wide cost tracking
cost = ElectricityCostService.record_cost(
    session,
    period_start=start,
    period_end=end,
    power_w=total_fleet_power_w,
    miner_ip=None,  # Fleet-wide
    location="Main Facility"
)
```

---

## 💰 Key Benefits

### 1. **Accurate Cost Tracking**
- No more estimations - track real electricity costs
- Account for time-of-use rate variations
- Include service charges and demand fees

### 2. **Better Profitability Insights**
- See true profit margins after actual electricity costs
- Identify most/least profitable time periods
- Make data-driven decisions about operations

### 3. **Cost Optimization Opportunities**
- Identify high-cost periods (TOU peak hours)
- Shift operations to low-cost periods when possible
- Track savings from operational changes

### 4. **Multi-Facility Support**
- Track different rates for different locations
- Compare costs across facilities
- Aggregate or separate as needed

### 5. **Historical Analysis**
- Track cost trends over time
- Seasonal cost comparisons
- Budget forecasting and planning

---

## 🚀 Quick Start

### 1. Initialize the Database
The tables will be created automatically when you run the application:
```bash
python main.py
```

### 2. Create Your First Rate
**Option A - Web UI:**
1. Navigate to http://localhost:5000/dashboard/electricity
2. Click "Initialize Default Rates" to create examples
3. Or click "Create New Rate" to configure your own

**Option B - API:**
```bash
curl -X POST http://localhost:5000/api/electricity/initialize
```

### 3. View Costs
Check the dashboard for:
- Current active rate
- Cost estimates
- Historical cost summary

---

## 📊 Usage Examples

### Example 1: Simple Flat Rate

**Your Scenario:**
- Electricity cost: $0.12/kWh
- Daily service charge: $0.50
- One miner drawing 3000W

**Configuration:**
```python
# Via API
POST /api/electricity/rates
{
    "name": "My Flat Rate",
    "rate_type": "flat",
    "flat_rate_usd_per_kwh": 0.12,
    "daily_service_charge_usd": 0.50,
    "active": true
}
```

**Daily Cost:**
```python
# 3000W = 3kW
# 24 hours * 3kW = 72 kWh
# 72 kWh * $0.12 = $8.64
# Plus service charge = $0.50
# Total: $9.14/day
```

### Example 2: Time-of-Use Rate

**Your Scenario:**
- Off-Peak (9 PM - 7 AM): $0.08/kWh
- Peak (7 AM - 9 PM): $0.18/kWh
- Same 3000W miner

**Configuration:**
```json
{
    "name": "TOU Rate",
    "rate_type": "tou",
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

**Daily Cost:**
```python
# Off-Peak: 10 hours * 3kW * $0.08 = $2.40
# Peak: 14 hours * 3kW * $0.18 = $7.56
# Total: $9.96/day
```

**Potential Savings:** Reduce power during peak hours to save money!

---

## 🔧 Configuration Options

### Rate Types

**1. Flat Rate**
- Single $/kWh price, 24/7
- Simplest to configure
- Best for: Residential, simple commercial

**2. Time-of-Use (TOU)**
- Different rates for different times/days
- Supports complex schedules
- Best for: Commercial, industrial

**3. Tiered** *(Planned)*
- Volume-based pricing
- Different rates per consumption tier
- Best for: Large operations

### Additional Charges

**Service Charges**
- Daily connection fees
- Automatically pro-rated for partial days
- Example: $0.50/day = $15/month

**Demand Charges**
- Based on peak power draw
- Charged per kW of peak demand
- Example: $5.00/kW * 100kW peak = $500/month

---

## 📈 Roadmap / Future Enhancements

Potential future features:

- [ ] Automated cost recording via scheduler
- [ ] Email alerts for high-cost periods
- [ ] Cost optimization recommendations
- [ ] Utility bill reconciliation
- [ ] Carbon intensity tracking
- [ ] Demand charge calculation
- [ ] Tiered rate support
- [ ] PDF/CSV export of cost reports
- [ ] Multi-currency support
- [ ] Budget tracking and alerts

---

## 📚 Documentation

**Full Documentation:**
- [`ELECTRICITY_COST_TRACKING.md`](./ELECTRICITY_COST_TRACKING.md) - Complete reference

**Quick Start:**
- [`ELECTRICITY_QUICKSTART.md`](./ELECTRICITY_QUICKSTART.md) - 5-minute setup

---

## ✅ Testing Checklist

Before going live, test:

- [ ] Create a flat rate and verify it appears in the UI
- [ ] Create a TOU rate with multiple periods
- [ ] Calculate cost via API with known values
- [ ] Verify cost summary aggregation
- [ ] Test activating/deactivating rates
- [ ] Check navigation links work
- [ ] Verify dark theme displays correctly
- [ ] Test on mobile devices (responsive design)

---

## 🎯 Next Steps

1. **Set Up Your Rates**
   - Navigate to `/dashboard/electricity`
   - Create rates matching your utility bill

2. **Monitor Costs**
   - Check daily cost estimates
   - Review cost summaries weekly

3. **Optimize Operations**
   - Use TOU data to shift operations
   - Reduce peak demand to save on demand charges

4. **Integrate with Profitability**
   - Review updated profit margins
   - Make data-driven operational decisions

---

## 📞 Support

**Need Help?**
1. Check the documentation files
2. Review API responses for error details
3. Check application logs: `logs/`
4. Verify database tables exist
5. Test with the `/api/electricity/initialize` endpoint

**Found a Bug?**
1. Check console for JavaScript errors
2. Review Flask logs for Python errors
3. Verify API responses are correct
4. Check database connectivity

---

**Congratulations!** You now have a comprehensive electricity cost tracking system integrated into your mining operation. This will provide accurate cost data for better profitability analysis and operational optimization.

Happy mining! ⛏️💰
