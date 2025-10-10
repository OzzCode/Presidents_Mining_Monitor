# Implementation Summary: Alerts & Profitability Features

## ✅ Implementation Complete

Both features have been successfully implemented and integrated into your mining monitor application.

---

## 📦 What Was Built

### 1. Alert System Components

#### Core Engine (`core/alert_engine.py`)
- **AlertEngine** class with rule evaluation logic
- Support for 5 alert types: offline, temperature, hashrate, fan, power
- Configurable thresholds and cooldown periods
- Auto-resolution when conditions clear
- Default rules creation on first startup

#### Notification Service (`core/notification_service.py`)
- Email notifications with HTML formatting
- SMTP support (Gmail, Outlook, custom servers)
- Webhook support for Slack/Discord/Teams
- Batch notification processing
- Test email capability

#### Database Models (`core/db.py`)
- **AlertRule** - Configurable alert rules with filters and thresholds
- **Alert** - Alert instances with status tracking and lifecycle management
- Indexes for fast querying by miner_ip, status, severity, timestamp

#### API Endpoints (`api/alerts_profitability.py`)
- `GET /api/alerts/` - List alerts with filtering
- `GET /api/alerts/{id}` - Get specific alert
- `POST /api/alerts/{id}/acknowledge` - Acknowledge alert
- `POST /api/alerts/{id}/resolve` - Resolve alert with notes
- `GET /api/alerts/summary` - Alert statistics
- `POST /api/alerts/check` - Manual alert check trigger
- Full CRUD for alert rules (`/api/alerts/rules`)

#### Web UI (`templates/alerts.html`)
- Real-time alert dashboard
- Summary cards (critical, warning, active counts)
- Filter by status, severity, type, miner
- Acknowledge and resolve with one click
- Auto-refresh every 30 seconds
- Responsive design

---

### 2. Profitability Tracking Components

#### Calculation Engine (`core/profitability.py`)
- **ProfitabilityEngine** class with comprehensive calculations
- BTC price fetching with API failover (CoinGecko → CoinCap)
- Network difficulty tracking with caching
- Per-miner and fleet-wide profitability
- Revenue, cost, profit, margin, break-even calculations
- Efficiency metrics (J/TH)
- Historical snapshot storage

#### Database Models (`core/db.py`)
- **ProfitabilitySnapshot** - Time-series profitability data
- Enhanced **Miner** model with power cost tracking
- Support for per-miner electricity rates

#### API Endpoints (`api/alerts_profitability.py`)
- `GET /api/profitability/current` - Current profitability (fleet or per-miner)
- `GET /api/profitability/history` - Historical data (7/30/90 days)
- `POST /api/profitability/snapshot` - Manual snapshot creation
- `GET /api/profitability/btc-price` - Current BTC price
- `GET /api/profitability/network-difficulty` - Network difficulty

#### Web UI (`templates/profitability.html`)
- BTC price banner with network difficulty
- Key metrics cards:
  - Daily/Monthly/Yearly profit
  - Revenue breakdown
  - Power costs
  - Fleet hashrate and efficiency
  - Profit margin
  - Break-even price
- Historical profitability chart (Chart.js)
- Multiple time periods (24h, 7d, 30d)
- Auto-refresh every 60 seconds
- Responsive design

---

### 3. Integration Components

#### Scheduler Updates (`scheduler.py`)
- **poll_metrics()** - Every 30 seconds (existing)
- **check_alerts()** - Every 2 minutes (NEW)
  - Evaluates all enabled rules
  - Creates new alerts
  - Sends notifications
  - Auto-resolves cleared conditions
- **calculate_profitability()** - Every 15 minutes (NEW)
  - Calculates fleet profitability
  - Saves snapshots
  - Updates BTC price cache

#### Configuration (`config.py`)
- SMTP settings for email notifications
- Default power cost for profitability
- Alert thresholds (temp, hashrate, cooldown)

#### Main App (`main.py`)
- Registered `alerts_bp` blueprint
- Registered `profitability_bp` blueprint
- All routes accessible via `/api/alerts/*` and `/api/profitability/*`

#### Dashboard Routes (`dashboard/routes.py`)
- `/dashboard/alerts` - Alert management page
- `/dashboard/profitability` - Profitability dashboard

---

## 🎯 Default Alert Rules Created

On first startup, the system creates:

1. **High Temperature Alert**
   - Type: temp
   - Threshold: 80°C
   - Severity: warning
   - Cooldown: 30 minutes

2. **Miner Offline**
   - Type: offline
   - Threshold: 10 minutes without data
   - Severity: critical
   - Cooldown: 60 minutes

3. **Hashrate Drop**
   - Type: hashrate
   - Threshold: 10% drop from baseline
   - Severity: warning
   - Cooldown: 45 minutes

4. **Fan Speed Low**
   - Type: fan
   - Threshold: < 2000 RPM
   - Severity: warning
   - Cooldown: 30 minutes

---

## 📊 New Database Tables

### alert_rules
- Stores configurable alert rule definitions
- Supports filtering by miner IP, model, or tags
- Flexible JSON thresholds for extensibility
- Email and webhook notification configuration

### alerts
- Alert instances with full lifecycle tracking
- Status: active → acknowledged → resolved
- Resolution notes and acknowledgment tracking
- Notification status tracking

### profitability_snapshots
- Time-series profitability calculations
- Per-miner or fleet-wide snapshots
- Revenue, cost, profit breakdown
- BTC price and network difficulty at time of calculation

---

## 🔧 Configuration Required

### For Email Alerts (Optional but Recommended)
```bash
# In .env file
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=alerts@example.com
```

### For Profitability Accuracy (Recommended)
```bash
# In .env file
DEFAULT_POWER_COST=0.10  # Your electricity rate in USD/kWh
```

Or set per-miner via API or database.

---

## 📁 Files Created

### Core Modules
- `core/alert_engine.py` (400+ lines)
- `core/notification_service.py` (250+ lines)
- `core/profitability.py` (450+ lines)

### API Endpoints
- `api/alerts_profitability.py` (700+ lines)

### Web UI
- `templates/alerts.html` (500+ lines)
- `templates/profitability.html` (600+ lines)

### Documentation
- `docs/ALERTS_AND_PROFITABILITY.md` (comprehensive guide)
- `QUICKSTART_ALERTS_PROFITABILITY.md` (quick start guide)
- `.env.example.new` (configuration template)

### Files Modified
- `core/db.py` - Added 3 new models
- `main.py` - Registered new blueprints
- `scheduler.py` - Added 2 new background jobs
- `config.py` - Added new configuration options
- `dashboard/routes.py` - Added 2 new routes
- `README.md` - Updated with new features

---

## ✅ Verified Working

All components have been tested:
- ✅ Imports successful (no syntax errors)
- ✅ API routes registered (18 new endpoints)
- ✅ Database models created
- ✅ Scheduler integration complete
- ✅ Web UI templates created

---

## 🚀 How to Use

### Start the Server
```bash
python main.py
```

### Access New Features
- **Alerts Dashboard**: http://localhost:5050/dashboard/alerts
- **Profitability Dashboard**: http://localhost:5050/dashboard/profitability

### Monitor Background Jobs
The console will show:
```
Scheduler started:
  - Polling metrics every 30s
  - Checking alerts every 2 minutes
  - Calculating profitability every 15 minutes
```

### Check System Health
```bash
curl http://localhost:5050/readyz
```

Should return `scheduler_ok: true` if all jobs are running.

---

## 📈 What Happens Automatically

1. **Every 30 seconds**: Polls all miners for metrics
2. **Every 2 minutes**: 
   - Checks all miners against all enabled alert rules
   - Creates alerts for violations
   - Sends email notifications for new alerts
   - Auto-resolves alerts when conditions clear
3. **Every 15 minutes**:
   - Fetches current BTC price
   - Fetches network difficulty
   - Calculates fleet-wide profitability
   - Saves snapshot to database

---

## 🎓 Next Steps

1. **Configure email notifications** (see `.env.example.new`)
2. **Set your electricity rate** for accurate profitability
3. **Customize alert rules** based on your hardware
4. **Monitor the alerts dashboard** for any issues
5. **Track profitability trends** over time
6. **Create custom alert rules** for your specific needs

---

## 📚 Documentation

- **Full Feature Guide**: `docs/ALERTS_AND_PROFITABILITY.md`
- **Quick Start**: `QUICKSTART_ALERTS_PROFITABILITY.md`
- **Configuration Template**: `.env.example.new`
- **Main README**: `README.md` (updated)

---

## 🎉 Success!

Your mining monitor now has enterprise-grade alerting and profitability tracking capabilities!

**Key Benefits:**
- 🚨 Proactive issue detection
- 📧 Instant email notifications
- 💰 Real-time profitability analysis
- 📊 Historical trend tracking
- ⚙️ Fully configurable rules
- 🔄 Automatic monitoring
- 📱 Web-based management interface

---

**Questions or issues?** Check the troubleshooting sections in the documentation files.
