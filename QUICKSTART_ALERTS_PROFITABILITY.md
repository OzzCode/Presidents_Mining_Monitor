# Quick Start: Alerts & Profitability Features

This guide will help you get started with the new alert and profitability features.

## Installation Complete ✓

The following components have been implemented:
- ✅ Alert database models
- ✅ Alert detection engine
- ✅ Email notification service
- ✅ Profitability calculation engine
- ✅ API endpoints for alerts and profitability
- ✅ Alert management UI
- ✅ Profitability dashboard UI
- ✅ Background scheduler integration

## Quick Start (5 minutes)

### 1. Start the Server
```bash
python main.py
```

The server will automatically:
- Create new database tables for alerts and profitability
- Initialize default alert rules
- Start background jobs for alert checking (every 2 min) and profitability calculation (every 15 min)

### 2. Access the New Dashboards

**Alerts Dashboard:**
```
http://localhost:5050/dashboard/alerts
```

**Profitability Dashboard:**
```
http://localhost:5050/dashboard/profitability
```

### 3. Test Alert System

The system comes with 4 default alert rules:
- 🌡️ **High Temperature** - Alerts when temp > 80°C
- 🔌 **Miner Offline** - Alerts when no data for 10+ minutes
- 📉 **Hashrate Drop** - Alerts when hashrate drops > 10%
- 🌀 **Fan Speed Low** - Alerts when fan < 2000 RPM

**Manual Alert Check:**
```bash
curl -X POST http://localhost:5050/api/alerts/check
```

**View Active Alerts:**
```bash
curl http://localhost:5050/api/alerts/?status=active
```

### 4. Configure Email Notifications (Optional)

Create a `.env` file:
```bash
# For Gmail
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=alerts@example.com

# For other providers
# SMTP_SERVER=smtp.office365.com  # Outlook
# SMTP_SERVER=smtp.mail.yahoo.com  # Yahoo
```

**Gmail Setup:**
1. Enable 2FA on your Google account
2. Generate app password: https://myaccount.google.com/apppasswords
3. Use the 16-character app password in SMTP_PASSWORD

**Test Email:**
```python
from core.notification_service import NotificationService
notifier = NotificationService()
notifier.send_test_email()
```

### 5. Configure Power Costs

Set your electricity rate for accurate profitability:

**Default for all miners (in .env):**
```bash
DEFAULT_POWER_COST=0.12  # USD per kWh
```

**Per-miner rates (via API):**
```bash
curl -X PUT http://localhost:5050/api/miners/{ip} \
  -H "Content-Type: application/json" \
  -d '{"power_price_usd_per_kwh": 0.15}'
```

Or directly in database:
```sql
UPDATE miners 
SET power_price_usd_per_kwh = 0.12 
WHERE miner_ip = '192.168.1.100';
```

## Key Features Overview

### Alert Management

**View alerts by status:**
- Active alerts: Currently unresolved issues
- Acknowledged: Operator is aware and working on it
- Resolved: Issue fixed and confirmed

**Alert actions:**
- **Acknowledge**: Mark as "seen" while investigating
- **Resolve**: Close the alert with resolution notes
- **Auto-resolve**: System automatically clears when condition normalizes

**Filter alerts:**
- By severity (critical, warning, info)
- By type (offline, temp, hashrate, fan, power)
- By specific miner IP
- By time range

### Profitability Tracking

**Real-time metrics:**
- Daily/Monthly/Yearly profit projections
- Revenue (BTC mined × price)
- Power costs (kWh × rate)
- Profit margin percentage
- Break-even BTC price
- Fleet efficiency (J/TH)

**Historical analysis:**
- 24-hour view
- 7-day trends
- 30-day analysis
- Profit/revenue/cost comparison charts

**Data sources:**
- BTC price: Live from CoinGecko/CoinCap
- Network difficulty: blockchain.info/mempool.space
- Hashrate: Real-time from your miners
- Power costs: Your configured rates

## API Examples

### Alerts

**Get summary:**
```bash
curl http://localhost:5050/api/alerts/summary
```

**Get critical alerts:**
```bash
curl "http://localhost:5050/api/alerts/?severity=critical&status=active"
```

**Acknowledge alert:**
```bash
curl -X POST http://localhost:5050/api/alerts/123/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"user": "john"}'
```

**Resolve with note:**
```bash
curl -X POST http://localhost:5050/api/alerts/123/resolve \
  -H "Content-Type: application/json" \
  -d '{"note": "Rebooted miner, back online", "user": "john"}'
```

**Create custom alert rule:**
```bash
curl -X POST http://localhost:5050/api/alerts/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "S19 Pro High Temp",
    "rule_type": "temp",
    "thresholds": {"temp_c": 75},
    "severity": "warning",
    "model_filter": "S19 Pro",
    "enabled": true,
    "notify_email": true
  }'
```

### Profitability

**Get fleet profitability:**
```bash
curl http://localhost:5050/api/profitability/current
```

**Get single miner profitability:**
```bash
curl "http://localhost:5050/api/profitability/current?miner_ip=192.168.1.100"
```

**Get 7-day history:**
```bash
curl "http://localhost:5050/api/profitability/history?days=7"
```

**Current BTC price:**
```bash
curl http://localhost:5050/api/profitability/btc-price
```

**Network difficulty:**
```bash
curl http://localhost:5050/api/profitability/network-difficulty
```

## Scheduler Jobs

The background scheduler runs three jobs:

1. **Metrics Polling** (every 30s)
   - Collects data from all miners
   - Stores in database

2. **Alert Checking** (every 2 minutes)
   - Evaluates all enabled alert rules
   - Creates alerts for violations
   - Auto-resolves cleared conditions
   - Sends email notifications

3. **Profitability Calculation** (every 15 minutes)
   - Calculates fleet-wide profitability
   - Saves snapshot to database
   - Updates BTC price and network difficulty cache

## Database Tables

New tables created:

**alert_rules** - Configurable alert rules
**alerts** - Alert instances with status tracking
**profitability_snapshots** - Historical profitability data

Existing miners table enhanced with:
- `power_price_usd_per_kwh` - Per-miner electricity rate
- `nominal_ths` - Expected hashrate
- `nominal_efficiency_j_per_th` - Expected efficiency

## Next Steps

1. **Configure email notifications** for critical alerts
2. **Set electricity rates** for accurate profitability
3. **Customize alert rules** based on your hardware
4. **Monitor trends** via the profitability dashboard
5. **Set up webhooks** for Slack/Discord integration (optional)

## Troubleshooting

**Alerts not triggering?**
- Check rules are enabled: `GET /api/alerts/rules`
- Verify thresholds match your hardware
- Check scheduler is running: `GET /readyz`

**Email not sending?**
- Verify SMTP settings in `.env`
- Test with `NotificationService().send_test_email()`
- Check application logs in `/logs`

**Profitability showing $0?**
- Ensure miners have valid metrics
- Check BTC price API is accessible
- Verify power costs are configured
- Wait for first profitability calculation (15 min)

**Performance issues?**
- Default settings are optimized for 100+ miners
- Adjust scheduler intervals if needed
- Check database indexes are created
- Monitor logs for errors

## Documentation

Full documentation: `/docs/ALERTS_AND_PROFITABILITY.md`

## Support

Questions or issues:
1. Check logs: `tail -f logs/app.log`
2. Review API responses for errors
3. Verify database schema with `sqlite3 db_files/metrics.db .schema`

---

**🎉 You're all set!** The system is now monitoring your miners for issues and calculating profitability in real-time.
