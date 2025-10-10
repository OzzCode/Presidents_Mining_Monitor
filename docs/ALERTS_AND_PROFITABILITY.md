# Alerts and Profitability Features

This document describes the newly implemented alert management and profitability tracking features.

## Overview

The mining monitor now includes:
- **Real-time alert system** with configurable rules and notifications
- **Profitability dashboard** with revenue, cost, and profit calculations
- **Historical tracking** of both alerts and profitability metrics
- **Email notifications** for critical events
- **Automated monitoring** integrated into the background scheduler

## Features

### 1. Alert System

#### Alert Types
- **Offline**: Miner hasn't reported in configured time window
- **Temperature**: Temperature exceeds threshold
- **Hashrate**: Hashrate drops below expected baseline
- **Fan**: Fan speed outside normal range
- **Power**: Power consumption anomalies

#### Alert Severities
- **Info**: Informational notifications
- **Warning**: Issues requiring attention
- **Critical**: Urgent problems requiring immediate action

#### Alert Lifecycle
1. **Active**: Alert triggered and awaiting acknowledgment
2. **Acknowledged**: Operator aware, working on resolution
3. **Resolved**: Manually resolved by operator
4. **Auto-resolved**: System detected condition cleared

#### Default Alert Rules
The system creates default rules on first startup:
- High temperature alert (>80°C)
- Miner offline (no data for 10+ minutes)
- Hashrate drop (>10% below baseline)
- Fan speed low (<2000 RPM)

### 2. Profitability Tracking

#### Metrics Calculated
- **Daily/Monthly/Yearly Profit**: Revenue minus power costs
- **Revenue**: Estimated BTC earnings × current BTC price
- **Power Costs**: kWh consumption × electricity rate
- **Profit Margin**: Percentage of revenue that is profit
- **Break-even Price**: BTC price at which profit = $0
- **Efficiency**: J/TH (watts per terahash)

#### Data Sources
- **BTC Price**: Live from CoinGecko or CoinCap APIs
- **Network Difficulty**: From blockchain.info or mempool.space
- **Hashrate/Power**: Real-time from miner metrics
- **Electricity Rates**: Per-miner configuration or default

#### Calculation Formula
```
Daily BTC = (Hashrate / Network Hashrate) × Blocks/Day × Block Reward
Daily Revenue (USD) = Daily BTC × BTC Price
Daily Cost (USD) = (Power kW × 24h) × Rate ($/kWh)
Daily Profit (USD) = Revenue - Cost
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# SMTP Configuration (for email alerts)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=alerts@example.com

# Profitability Configuration
DEFAULT_POWER_COST=0.10  # USD per kWh (default)

# Alert Thresholds (optional overrides)
TEMP_THRESHOLD=80  # Celsius
HASHRATE_DROP_THRESHOLD=0.9  # 0.9 = 10% drop triggers alert
ALERT_COOLDOWN_MINUTES=30  # Time before re-alerting
```

### Per-Miner Power Costs

You can set individual power costs for each miner in the `miners` table:
```sql
UPDATE miners 
SET power_price_usd_per_kwh = 0.12 
WHERE miner_ip = '192.168.1.100';
```

## API Endpoints

### Alerts API

#### Get Alerts
```
GET /api/alerts/
Query params: status, severity, miner_ip, alert_type, limit, since
```

#### Get Alert Summary
```
GET /api/alerts/summary
Returns: total, active, critical_active, last_24h counts
```

#### Acknowledge Alert
```
POST /api/alerts/{alert_id}/acknowledge
Body: {"user": "username"}
```

#### Resolve Alert
```
POST /api/alerts/{alert_id}/resolve
Body: {"note": "Fixed by rebooting", "user": "username"}
```

#### Trigger Alert Check
```
POST /api/alerts/check
Manually trigger alert evaluation for all miners
```

#### Alert Rules Management
```
GET /api/alerts/rules
GET /api/alerts/rules/{rule_id}
POST /api/alerts/rules
PUT /api/alerts/rules/{rule_id}
DELETE /api/alerts/rules/{rule_id}
POST /api/alerts/rules/init-defaults
```

### Profitability API

#### Get Current Profitability
```
GET /api/profitability/current?miner_ip={ip}
Omit miner_ip for fleet-wide calculation
```

#### Get Historical Profitability
```
GET /api/profitability/history?miner_ip={ip}&days=7
```

#### Create Snapshot
```
POST /api/profitability/snapshot?miner_ip={ip}
Manually trigger profitability calculation and save
```

#### Get BTC Price
```
GET /api/profitability/btc-price
Returns: current BTC price in USD
```

#### Get Network Difficulty
```
GET /api/profitability/network-difficulty
```

## Web UI

### Alerts Dashboard
Access at: `http://localhost:5050/dashboard/alerts`

Features:
- Real-time summary cards (critical, warning, active counts)
- Filter by status, severity, type, and miner
- Acknowledge and resolve alerts with notes
- Manual alert check trigger
- Auto-refresh every 30 seconds

### Profitability Dashboard
Access at: `http://localhost:5050/dashboard/profitability`

Features:
- Live BTC price and network difficulty
- Key metrics cards (profit, revenue, costs, hashrate)
- Break-even analysis
- Historical profitability charts (24h, 7d, 30d)
- Efficiency metrics (J/TH)
- Auto-refresh every 60 seconds

## Background Jobs

The scheduler now runs three jobs:

1. **Metrics Polling**: Every 30 seconds (configurable via `POLL_INTERVAL`)
   - Collects metrics from all miners
   
2. **Alert Checking**: Every 2 minutes
   - Evaluates all enabled alert rules
   - Triggers notifications for new alerts
   - Auto-resolves cleared conditions

3. **Profitability Calculation**: Every 15 minutes
   - Calculates fleet-wide profitability
   - Saves snapshot to database
   - Updates BTC price and network difficulty cache

## Database Schema

### New Tables

#### `alert_rules`
Configurable alert rules with thresholds and notification settings.

#### `alerts`
Alert instances with status tracking and resolution notes.

#### `profitability_snapshots`
Time-series profitability calculations for trending.

## Email Notifications

### Gmail Setup Example
1. Enable 2-factor authentication on your Google account
2. Generate an app-specific password: https://myaccount.google.com/apppasswords
3. Configure `.env`:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=youremail@gmail.com
SMTP_PASSWORD=your-16-char-app-password
ALERT_EMAIL=recipient@example.com
```

### Notification Format
- **Subject**: 🚨 CRITICAL: offline - 192.168.1.100
- **Body**: HTML formatted with alert details, severity, timestamp, and resolution instructions

### Webhook Notifications
You can also configure webhook URLs for each alert rule to integrate with:
- Slack
- Discord
- Microsoft Teams
- Custom webhooks

## Creating Custom Alert Rules

### Via API
```bash
curl -X POST http://localhost:5050/api/alerts/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Power Consumption",
    "rule_type": "power",
    "thresholds": {"max_power_w": 3500},
    "severity": "warning",
    "enabled": true,
    "notify_email": true
  }'
```

### Via Database
```sql
INSERT INTO alert_rules (name, rule_type, thresholds, severity, enabled)
VALUES (
  'S19 Pro High Temp',
  'temp',
  '{"temp_c": 75}',
  'warning',
  1
);
```

## Best Practices

### Alert Configuration
- Set cooldown periods to avoid alert fatigue (30-60 minutes)
- Use severity levels appropriately (critical for offline, warning for temp)
- Configure per-miner rules for different hardware models
- Test email notifications with test alerts

### Profitability Monitoring
- Update power costs regularly based on utility rates
- Monitor break-even price relative to market trends
- Track profit margin to identify optimization opportunities
- Use historical data to identify seasonal patterns

### Performance
- Default check interval (2 minutes) balances responsiveness and load
- Profitability calculations cache API calls to avoid rate limits
- Database indexes on miner_ip and timestamp for fast queries

## Troubleshooting

### Alerts Not Triggering
1. Check alert rules are enabled: `GET /api/alerts/rules`
2. Verify thresholds are configured correctly
3. Check scheduler is running: `GET /readyz`
4. Review logs for alert evaluation errors

### Email Notifications Not Sending
1. Test SMTP configuration: Use notification service test method
2. Check SMTP credentials are correct
3. Verify SMTP port (587 for TLS, 465 for SSL)
4. Check spam folder for test emails
5. Review application logs for SMTP errors

### Profitability Data Missing
1. Ensure miners have valid metrics: `GET /api/metrics`
2. Check BTC price API is accessible
3. Verify power costs are configured
4. Check profitability job is scheduled and running

## Future Enhancements

Potential additions:
- SMS notifications via Twilio
- Mobile push notifications
- Alert escalation policies
- Custom profitability scenarios (what-if analysis)
- Pool-level profitability tracking
- ROI calculator based on hardware costs
- Integration with accounting software

## Support

For issues or questions:
1. Check application logs in `/logs` directory
2. Review database state via `/api/debug` endpoints
3. Verify configuration in `.env` file
4. Check API responses for error messages
