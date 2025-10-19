# Electricity Cost Tracking - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Run the Application
```bash
python main.py
```

The electricity tracking tables will be created automatically on first run.

### Step 2: Access the Dashboard
Open your browser and navigate to:
```
http://localhost:5000/dashboard/electricity
```

### Step 3: Create Your First Rate

**Option A: Use Default Examples**
1. Click **"Initialize Default Rates"** button
2. This creates two example rates:
   - **Flat Rate - Residential**: Simple $0.12/kWh
   - **TOU - Summer 2024**: Time-of-use with peak/off-peak pricing

**Option B: Create Custom Rate**
1. Click **"➕ Create New Rate"**
2. Fill in the form:
   - **Name**: e.g., "My Electricity Rate"
   - **Rate Type**: Choose "Flat Rate" or "Time-of-Use"
   - **Flat Rate**: Enter your $/kWh rate (e.g., 0.12)
   - **Location**: (Optional) e.g., "Main Facility"
3. Click **"Save Rate"**

### Step 4: View Your Costs

The dashboard will show:
- ✅ Active rate configurations
- ✅ Current electricity rate
- ✅ Estimated daily/monthly costs
- ✅ Cost history for last 30 days

## 📊 Creating a Time-of-Use (TOU) Rate

If your utility uses time-of-use pricing:

1. Click **"➕ Create New Rate"**
2. Select **"Time-of-Use (TOU)"** as Rate Type
3. Click **"➕ Add Period"** for each rate period:
   
   **Example: Simple Peak/Off-Peak**
   
   **Off-Peak Period:**
   - Period Name: `Off-Peak`
   - Rate: `0.08`
   - Start Hour: `21` (9 PM)
   - End Hour: `7` (7 AM)
   - Days: ✓ All days
   
   **Peak Period:**
   - Period Name: `Peak`
   - Rate: `0.18`
   - Start Hour: `7` (7 AM)
   - End Hour: `21` (9 PM)
   - Days: ✓ All days

4. Click **"Save Rate"**

## 🔌 API Usage Examples

### Get Current Electricity Rate
```bash
curl http://localhost:5000/api/electricity/current-rate
```

Response:
```json
{
    "ok": true,
    "rate": {
        "id": 1,
        "name": "TOU - Summer 2024",
        "rate_type": "tou",
        "current_rate_usd_per_kwh": 0.08,
        "timestamp": "2024-01-15T14:30:00Z"
    }
}
```

### Calculate Cost for a Period
```bash
curl -X POST http://localhost:5000/api/electricity/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "power_w": 3000,
    "start_time": "2024-01-15T00:00:00Z",
    "end_time": "2024-01-16T00:00:00Z"
  }'
```

Response:
```json
{
    "ok": true,
    "calculation": {
        "total_kwh": 72.0,
        "energy_cost_usd": 8.10,
        "avg_rate_usd_per_kwh": 0.1125,
        "tou_breakdown": {
            "Off-Peak": 3.20,
            "Peak": 4.90
        }
    }
}
```

### Get Cost Summary
```bash
curl "http://localhost:5000/api/electricity/costs/summary?start_date=2024-01-01&end_date=2024-01-31"
```

## 💡 Common Scenarios

### Scenario 1: Flat Rate Billing
**Your utility charges:** $0.12/kWh flat rate, $0.50/day service charge

**Configuration:**
```json
{
    "name": "Flat Rate 2024",
    "rate_type": "flat",
    "flat_rate_usd_per_kwh": 0.12,
    "daily_service_charge_usd": 0.50
}
```

### Scenario 2: Simple TOU (Weekday Peak/Off-Peak)
**Your utility charges:**
- Weekdays 5-9 PM: $0.22/kWh (Peak)
- All other times: $0.08/kWh (Off-Peak)

**Configuration:**
```json
{
    "name": "TOU Weekday Peak",
    "rate_type": "tou",
    "tou_schedule": [
        {
            "name": "Off-Peak",
            "rate": 0.08,
            "days": [0,1,2,3,4,5,6],
            "start_hour": 0,
            "end_hour": 17
        },
        {
            "name": "Peak",
            "rate": 0.22,
            "days": [0,1,2,3,4],
            "start_hour": 17,
            "end_hour": 21
        },
        {
            "name": "Off-Peak Night",
            "rate": 0.08,
            "days": [0,1,2,3,4,5,6],
            "start_hour": 21,
            "end_hour": 24
        },
        {
            "name": "Weekend",
            "rate": 0.08,
            "days": [5,6],
            "start_hour": 17,
            "end_hour": 21
        }
    ]
}
```

### Scenario 3: Multi-Location Setup
**You have:** 2 facilities with different rates

**Steps:**
1. Create rate #1 with `location: "Facility A"`
2. Create rate #2 with `location: "Facility B"`
3. Both can be active simultaneously (different locations)

## 📈 Integration with Profitability

The electricity costs automatically integrate with your profitability tracking:

**Before (Simple):**
```
Daily Profit = (BTC Revenue) - (Fixed Power Cost)
```

**After (Accurate):**
```
Daily Profit = (BTC Revenue) - (Actual TOU-based Power Cost)
```

Navigate to **Profitability** page to see updated calculations with real electricity costs!

## 🎯 Pro Tips

### Tip 1: Load Shifting
If you have TOU rates, consider:
- Running miners at full power during off-peak hours
- Reducing power during peak hours
- Can save 30-50% on electricity costs!

### Tip 2: Monitor Your Bill
- Track your actual utility bill
- Compare with the cost summary
- Adjust rates if needed

### Tip 3: Seasonal Rates
Many utilities have seasonal pricing:
- Create "Summer TOU 2024"
- Create "Winter TOU 2024"
- Activate the appropriate one for the season

### Tip 4: Add Service Charges
Don't forget to include:
- Daily connection fees
- Demand charges (if applicable)
- Taxes/fees (include in rate if needed)

## 🔧 Troubleshooting

### Problem: Can't see the Electricity menu
**Solution:** Make sure you're logged in and refresh the page.

### Problem: Costs seem too high/low
**Check:**
1. Power consumption is correct (watts)
2. Rate values are in $/kWh not $/MWh
3. Time zone is correct
4. TOU schedule covers all hours

### Problem: TOU breakdown not showing
**Solution:** Make sure your rate type is "tou" and you've added TOU periods.

### Problem: No cost history
**Solution:** Costs are recorded by your application over time. Wait for the scheduler to run or manually trigger cost recording.

## 📚 Next Steps

1. ✅ **Set up your electricity rate** - Done!
2. 📊 **Monitor costs** - Check dashboard daily
3. 🔍 **Optimize operations** - Use cost data to save money
4. 📈 **Review profitability** - See real profit margins

**Need more help?** See the full documentation:
- [ELECTRICITY_COST_TRACKING.md](./ELECTRICITY_COST_TRACKING.md)

---

**Questions?** Open an issue or check the logs in `logs/` directory.
