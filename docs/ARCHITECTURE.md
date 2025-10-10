# System Architecture: Alerts & Profitability

## Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Application (main.py)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐     │
│  │   API Layer  │  │  Dashboard   │  │  Background Jobs  │     │
│  │              │  │   Routes     │  │   (APScheduler)   │     │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬─────────┘     │
│         │                 │                     │                │
│         └─────────────────┴─────────────────────┘                │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│  Alert Engine │   │ Profitability│   │ Notification │
│               │   │    Engine    │   │   Service    │
└───────┬───────┘   └──────┬───────┘   └──────┬───────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   SQLite Database     │
                │  (metrics.db + WAL)   │
                └───────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Metrics    │   │    Alerts    │   │Profitability │
│              │   │  AlertRules  │   │  Snapshots   │
│              │   │              │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Data Flow

### 1. Metric Collection Flow
```
Miners (CGMiner API)
        │
        ▼
Discovery Scanner ──> MinerClient
        │
        ▼
Metric Record ──> SQLite Database
        │
        └──> Triggers Alert Checks
```

### 2. Alert Processing Flow
```
Scheduled Job (every 2 min)
        │
        ▼
AlertEngine.check_all_miners()
        │
        ├──> Query latest metrics
        │
        ├──> Evaluate each rule
        │    │
        │    ├──> Check thresholds
        │    ├──> Check cooldown
        │    └──> Check rule scope
        │
        ├──> Create new alerts
        │    │
        │    └──> Save to database
        │
        ├──> Auto-resolve cleared alerts
        │
        └──> Send notifications
             │
             ├──> Email (SMTP)
             └──> Webhook (HTTP)
```

### 3. Profitability Calculation Flow
```
Scheduled Job (every 15 min)
        │
        ├──> Fetch BTC Price (CoinGecko/CoinCap)
        │
        ├──> Fetch Network Difficulty (blockchain.info)
        │
        ▼
Query Latest Metrics
        │
        ├──> Per-Miner or Fleet-Wide
        │
        ▼
Calculate Profitability
        │
        ├──> Daily BTC = (HR / Net HR) × Blocks × Reward
        ├──> Revenue = Daily BTC × Price
        ├──> Cost = Power kW × 24h × Rate
        ├──> Profit = Revenue - Cost
        └──> Break-even = Cost / Daily BTC
        │
        ▼
Save Snapshot to Database
```

## API Request Flow

### Alert API Request
```
Client Request
        │
        ▼
Flask Blueprint (alerts_bp)
        │
        ▼
Endpoint Handler
        │
        ├──> Validate parameters
        │
        ├──> Create session
        │
        ├──> Query database
        │    │
        │    └──> Apply filters
        │
        ├──> Serialize results
        │
        └──> Return JSON response
```

### Profitability API Request
```
Client Request
        │
        ▼
Flask Blueprint (profitability_bp)
        │
        ▼
ProfitabilityEngine context manager
        │
        ├──> Get cached BTC price (5 min TTL)
        │
        ├──> Get cached difficulty (30 min TTL)
        │
        ├──> Query metrics
        │
        ├──> Calculate profitability
        │
        ├──> Format response
        │
        └──> Return JSON
```

## Background Job Architecture

```
APScheduler (BackgroundScheduler)
        │
        ├──> Job 1: poll_metrics (30s)
        │    │
        │    └──> For each discovered miner:
        │         │
        │         ├──> Fetch CGMiner data
        │         ├──> Normalize payload
        │         └──> Insert Metric record
        │
        ├──> Job 2: check_alerts (2 min)
        │    │
        │    └──> AlertEngine.check_all_miners()
        │         │
        │         ├──> Evaluate rules
        │         ├──> Create alerts
        │         ├──> Auto-resolve
        │         └──> NotificationService.batch_notify()
        │
        └──> Job 3: calculate_profitability (15 min)
             │
             └──> ProfitabilityEngine.calculate_fleet()
                  │
                  ├──> Fetch external data
                  ├──> Calculate metrics
                  └──> Save snapshot
```

## Database Schema

### Core Tables (Existing)
```
metrics
├─ id (PK)
├─ timestamp (indexed)
├─ miner_ip (indexed)
├─ power_w
├─ hashrate_ths
├─ elapsed_s
├─ avg_temp_c
└─ avg_fan_rpm

miners
├─ id (PK)
├─ miner_ip (unique, indexed)
├─ model
├─ vendor
├─ power_price_usd_per_kwh (NEW)
├─ nominal_ths (NEW)
└─ nominal_efficiency_j_per_th (NEW)
```

### Alert Tables (New)
```
alert_rules
├─ id (PK)
├─ name
├─ rule_type (indexed)
├─ enabled (indexed)
├─ thresholds (JSON)
├─ severity
├─ cooldown_minutes
├─ notify_email
├─ notify_webhook
├─ webhook_url
└─ miner_ip (indexed, nullable)

alerts
├─ id (PK)
├─ created_at (indexed)
├─ rule_id (indexed)
├─ miner_ip (indexed)
├─ alert_type (indexed)
├─ severity (indexed)
├─ status (indexed)
├─ message
├─ details (JSON)
├─ acknowledged_at
├─ resolved_at
└─ notification_status
```

### Profitability Table (New)
```
profitability_snapshots
├─ id (PK)
├─ timestamp (indexed)
├─ miner_ip (indexed, nullable)
├─ btc_price_usd
├─ network_difficulty
├─ hashrate_ths
├─ power_w
├─ estimated_btc_per_day
├─ estimated_revenue_usd_per_day
├─ daily_power_cost_usd
├─ daily_profit_usd
├─ profit_margin_pct
└─ break_even_btc_price
```

## Integration Points

### External APIs
```
BTC Price
├─ CoinGecko API (primary)
│  └─ GET api.coingecko.com/api/v3/simple/price
│
└─ CoinCap API (fallback)
   └─ GET api.coincap.io/v2/assets/bitcoin

Network Difficulty
├─ Blockchain.info (primary)
│  └─ GET blockchain.info/q/getdifficulty
│
└─ Mempool.space (fallback)
   └─ GET mempool.space/api/v1/difficulty-adjustment
```

### Notification Channels
```
Email (SMTP)
├─ Gmail
├─ Outlook/Office365
├─ Yahoo
└─ Custom SMTP servers

Webhooks (HTTP POST)
├─ Slack
├─ Discord
├─ Microsoft Teams
└─ Custom endpoints
```

## Web UI Architecture

### Frontend Stack
```
HTML5
├─ Semantic markup
└─ Responsive design

CSS3
├─ Custom styles
├─ Grid/Flexbox layouts
└─ Animations

JavaScript (Vanilla)
├─ Fetch API for requests
├─ Chart.js for graphs
├─ Auto-refresh timers
└─ DOM manipulation
```

### Page Structure
```
alerts.html
├─ Summary cards (critical, warning, active)
├─ Filters (status, severity, type, IP)
├─ Alert list with actions
└─ Auto-refresh (30s)

profitability.html
├─ BTC price banner
├─ Metrics grid (8 cards)
├─ Historical chart (Chart.js)
└─ Auto-refresh (60s)
```

## Security Considerations

### API Security
- CORS enabled for cross-origin requests
- Input validation on all endpoints
- SQL injection protection via SQLAlchemy ORM
- Rate limiting considerations for production

### Email Security
- Supports TLS/STARTTLS
- App-specific passwords recommended
- No credentials in source code
- Environment variable configuration

### Database Security
- WAL mode for concurrent access
- Check same thread disabled for scheduler
- Prepared statements via ORM
- Connection pooling

## Performance Optimizations

### Caching
```
BTC Price Cache
└─ TTL: 5 minutes
   └─ Reduces API calls during profitability checks

Network Difficulty Cache
└─ TTL: 30 minutes
   └─ Difficulty changes every ~2 weeks

Database Indexes
├─ miner_ip (all tables)
├─ timestamp (metrics, alerts, snapshots)
├─ status (alerts)
└─ rule_type (alert_rules)
```

### Query Optimization
```
Latest Metrics Query
└─ Subquery for max(timestamp) per miner
   └─ Join to get full record
      └─ Indexed for fast retrieval

Alert Evaluation
└─ Single query for all rules
   └─ In-memory evaluation
      └─ Batch insert new alerts

Profitability History
└─ Date range filter on indexed timestamp
   └─ Order by timestamp ASC
      └─ Limited result set
```

## Scalability Notes

### Current Capacity
- Designed for 100-500 miners
- SQLite with WAL handles concurrent reads
- Background jobs optimized for minimal load
- Web UI auto-refresh balanced for UX

### Future Scaling Options
- PostgreSQL/MySQL for 1000+ miners
- Redis for caching and job queue
- Celery for distributed task processing
- Load balancer for multiple app instances
- Time-series database for metrics (InfluxDB)

## Error Handling

### Retry Logic
```
API Fetches
└─ Try primary → Fallback to secondary → Return None

Email Notifications
└─ Log error → Mark as failed → Retry on next check

Database Operations
└─ Transaction rollback → Log error → Continue processing
```

### Logging
```
Application Logs
├─ logs/app.log (rotating)
├─ JSON or text format
└─ Retention: 7 days

Database Logs (if enabled)
├─ error_events table
├─ Structured context
└─ Queryable via API
```

## Deployment Architecture

### Development
```
Windows/macOS/Linux
├─ Python 3.10+
├─ SQLite (bundled)
├─ Flask dev server
└─ Background scheduler in-process
```

### Production (Recommended)
```
Linux Server
├─ Python 3.10+ with venv
├─ Gunicorn/Waitress (WSGI)
├─ Nginx (reverse proxy)
├─ SQLite or PostgreSQL
├─ Systemd service for scheduler
└─ Log aggregation (optional)
```

---

This architecture provides a robust, scalable foundation for enterprise mining operations while maintaining simplicity for small-scale deployments.
