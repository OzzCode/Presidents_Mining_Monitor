# Remote Management System

## Overview

The Remote Management System provides comprehensive remote control capabilities for your Bitcoin mining fleet, enabling you to manage miners from anywhere without physical access.

## Features

### ✅ Remote Operations
- **Reboot Miners**: Restart individual miners or bulk reboot
- **Pool Switching**: Change mining pools on-the-fly
- **Configuration Backup**: Save and restore miner configurations
- **Command History**: Audit log of all remote commands
- **Power Scheduling**: Automated on/off schedules (TOU optimization)

### ✅ Bulk Operations
- Reboot multiple miners simultaneously
- Switch entire fleet to new pool
- Group operations by location, tags, or custom filters

### ✅ Safety & Auditing
- Full command history with timestamps
- User tracking (who executed what)
- Success/failure status tracking
- Duration monitoring
- Batch operation grouping

## Database Models

### PowerSchedule
Scheduled power on/off times for cost optimization:

```python
{
    "id": 1,
    "name": "Off-Peak Mining",
    "description": "Power down during peak electricity hours",
    "enabled": true,
    "schedule_type": "weekly",  # 'weekly', 'daily', 'one-time'
    "miner_ip": null,  # null = all miners
    "location": "Main Facility",
    "weekly_schedule": [
        {
            "day": 0,  # Monday
            "start_hour": 17,  # 5 PM
            "end_hour": 21,  # 9 PM
            "action": "off"  # Turn off during peak hours
        }
    ],
    "power_limit_w": 2500,  # Reduce power instead of full shutdown
    "timezone": "America/New_York",
    "electricity_rate_id": 1  # Link to TOU rate
}
```

### CommandHistory
Audit log of all remote commands:

```python
{
    "id": 1,
    "timestamp": "2024-01-15T14:30:00Z",
    "command_type": "reboot",  # 'reboot', 'pool_switch', 'power_on', 'power_off'
    "miner_ip": "10.0.0.100",
    "parameters": {"reason": "firmware_update"},
    "status": "success",  # 'pending', 'success', 'failed', 'timeout'
    "response": {"result": "rebooting"},
    "error_message": null,
    "sent_at": "2024-01-15T14:30:00Z",
    "completed_at": "2024-01-15T14:30:02Z",
    "duration_ms": 2150,
    "initiated_by": "admin",
    "source": "manual",  # 'manual', 'scheduled', 'automatic'
    "batch_id": "abc-123"  # Groups bulk operations
}
```

### MinerConfigBackup
Configuration backups for recovery:

```python
{
    "id": 1,
    "miner_ip": "10.0.0.100",
    "backup_name": "Pre-firmware update",
    "description": "Backup before updating to v2.0",
    "backup_type": "manual",  # 'manual', 'automatic', 'pre_update'
    "config_data": {
        "pools": [...],
        "frequencies": [...],
        "voltage": {...},
        # Full miner configuration
    },
    "created_at": "2024-01-15T10:00:00Z",
    "created_by": "admin",
    "is_validated": false
}
```

## API Endpoints

### Reboot Operations

#### POST /api/remote/reboot/{miner_ip}
Reboot a single miner.

**Response:**
```json
{
    "ok": true,
    "message": "Reboot command sent to 10.0.0.100",
    "command_id": 42,
    "status": "success"
}
```

#### POST /api/remote/reboot/bulk
Reboot multiple miners.

**Request:**
```json
{
    "miner_ips": ["10.0.0.100", "10.0.0.101", "10.0.0.102"]
}
```

**Response:**
```json
{
    "ok": true,
    "message": "Bulk reboot initiated for 3 miners",
    "results": {
        "batch_id": "abc-123-def-456",
        "total": 3,
        "successful": 2,
        "failed": 1,
        "commands": [
            {"miner_ip": "10.0.0.100", "status": "success", "error": null},
            {"miner_ip": "10.0.0.101", "status": "success", "error": null},
            {"miner_ip": "10.0.0.102", "status": "failed", "error": "Connection timeout"}
        ]
    }
}
```

### Pool Switching

#### POST /api/remote/pool/switch/{miner_ip}
Switch mining pool for a single miner.

**Request:**
```json
{
    "pool_url": "stratum+tcp://pool.example.com:3333",
    "worker_name": "username.worker1",
    "pool_password": "x",
    "pool_number": 0
}
```

#### POST /api/remote/pool/switch/bulk
Switch pool for multiple miners.

**Request:**
```json
{
    "miner_ips": ["10.0.0.100", "10.0.0.101"],
    "pool_url": "stratum+tcp://pool.example.com:3333",
    "worker_name": "username.worker1",
    "pool_password": "x"
}
```

### Configuration Backup

#### POST /api/remote/backup/{miner_ip}
Create a configuration backup.

**Request:**
```json
{
    "backup_name": "Pre-update backup",
    "description": "Before firmware v2.0 update"
}
```

#### GET /api/remote/backups
List all configuration backups.

**Query Parameters:**
- `miner_ip`: Filter by miner IP
- `limit`: Max results (default: 50)

#### GET /api/remote/backups/{backup_id}
Get a specific backup with full configuration data.

### Command History

#### GET /api/remote/commands/history
Get command execution history.

**Query Parameters:**
- `miner_ip`: Filter by miner
- `command_type`: Filter by type ('reboot', 'pool_switch', etc.)
- `status`: Filter by status ('success', 'failed', 'pending')
- `limit`: Max results (default: 100)

#### GET /api/remote/commands/stats
Get command statistics for last 24 hours.

**Response:**
```json
{
    "ok": true,
    "stats": {
        "period": "last_24_hours",
        "total": 45,
        "successful": 42,
        "failed": 3,
        "pending": 0,
        "by_type": {
            "reboot": 20,
            "pool_switch": 15,
            "power_on": 5,
            "power_off": 5
        }
    }
}
```

### Power Scheduling

#### GET /api/remote/schedule/power
List all power schedules.

**Query Parameters:**
- `enabled_only`: Show only enabled schedules

#### POST /api/remote/schedule/power
Create a new power schedule.

**Request:**
```json
{
    "name": "Peak Hour Shutdown",
    "description": "Turn off during expensive peak hours",
    "schedule_type": "weekly",
    "weekly_schedule": [
        {
            "day": 0,
            "start_hour": 17,
            "end_hour": 21,
            "action": "off"
        }
    ],
    "location": "Main Facility",
    "enabled": true,
    "timezone": "America/New_York",
    "electricity_rate_id": 1
}
```

#### PUT /api/remote/schedule/power/{schedule_id}
Update a power schedule.

#### DELETE /api/remote/schedule/power/{schedule_id}
Delete a power schedule.

#### POST /api/remote/schedule/power/{schedule_id}/toggle
Enable/disable a schedule.

#### POST /api/remote/schedule/check
Manually trigger schedule check and execution.

## Web Interface

Access the Remote Control Center at:
```
http://your-server:5000/dashboard/remote
```

### Dashboard Tabs

**1. Control Panel**
- Reboot miners (individual or bulk)
- Switch mining pools
- Create configuration backups
- Visual miner selection with checkboxes

**2. Power Schedules**
- View all schedules
- Enable/disable schedules
- Create new schedules
- Integrated with TOU electricity rates

**3. Backups**
- View all configuration backups
- Download/view configurations
- Validate backups

**4. Command History**
- Real-time command execution log
- Filter by type, status, miner
- Success/failure details
- Duration tracking

## Usage Examples

### Python

```python
from core.remote_control import RemoteControlService, PowerScheduleService
from core.db import SessionLocal

session = SessionLocal()

# Reboot a miner
cmd = RemoteControlService.reboot_miner(
    session, "10.0.0.100", initiated_by="admin"
)
print(f"Reboot status: {cmd.status}")

# Bulk reboot
results = RemoteControlService.bulk_reboot(
    session, 
    ["10.0.0.100", "10.0.0.101", "10.0.0.102"],
    initiated_by="admin"
)
print(f"Successful: {results['successful']}, Failed: {results['failed']}")

# Switch pool
cmd = RemoteControlService.switch_pool(
    session,
    "10.0.0.100",
    pool_url="stratum+tcp://pool.example.com:3333",
    worker_name="username.worker1",
    pool_password="x",
    initiated_by="admin"
)

# Create backup
backup = RemoteControlService.backup_config(
    session,
    "10.0.0.100",
    backup_name="Pre-update backup",
    created_by="admin"
)
print(f"Backup ID: {backup.id}")

# Create power schedule
schedule = PowerScheduleService.create_schedule(
    session,
    name="Peak Hour Shutdown",
    schedule_type="weekly",
    weekly_schedule=[
        {
            "day": 0,
            "start_hour": 17,
            "end_hour": 21,
            "action": "off"
        }
    ],
    location="Main Facility",
    created_by="admin"
)
```

### cURL

```bash
# Reboot a miner
curl -X POST http://localhost:5000/api/remote/reboot/10.0.0.100

# Bulk reboot
curl -X POST http://localhost:5000/api/remote/reboot/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "miner_ips": ["10.0.0.100", "10.0.0.101"]
  }'

# Switch pool
curl -X POST http://localhost:5000/api/remote/pool/switch/10.0.0.100 \
  -H "Content-Type: application/json" \
  -d '{
    "pool_url": "stratum+tcp://pool.example.com:3333",
    "worker_name": "username.worker1"
  }'

# Create backup
curl -X POST http://localhost:5000/api/remote/backup/10.0.0.100 \
  -H "Content-Type: application/json" \
  -d '{
    "backup_name": "Pre-update backup"
  }'

# Get command history
curl "http://localhost:5000/api/remote/commands/history?limit=10"

# Get command stats
curl http://localhost:5000/api/remote/commands/stats
```

### JavaScript

```javascript
// Reboot miners
async function rebootMiners(minerIps) {
    const res = await fetch('/api/remote/reboot/bulk', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({miner_ips: minerIps})
    });
    const data = await res.json();
    console.log(`${data.results.successful} miners rebooted successfully`);
}

// Switch pool
async function switchPool(minerIps, poolUrl, workerName) {
    const res = await fetch('/api/remote/pool/switch/bulk', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            miner_ips: minerIps,
            pool_url: poolUrl,
            worker_name: workerName
        })
    });
    return await res.json();
}

// Get command history
async function getHistory() {
    const res = await fetch('/api/remote/commands/history?limit=50');
    const data = await res.json();
    return data.commands;
}
```

## Common Use Cases

### 1. Emergency Reboot All Miners
```bash
# Get all active miners and reboot them
curl http://localhost:5000/api/miners | \
  jq -r '.miners[].ip' | \
  jq -R -s -c 'split("\n") | map(select(length > 0))' | \
  curl -X POST http://localhost:5000/api/remote/reboot/bulk \
    -H "Content-Type: application/json" \
    -d @-
```

### 2. Pool Migration
```python
# Switch entire fleet to new pool
from core.remote_control import RemoteControlService
from core.db import SessionLocal, Miner

session = SessionLocal()
miners = session.query(Miner).all()
miner_ips = [m.miner_ip for m in miners]

results = RemoteControlService.bulk_pool_switch(
    session,
    miner_ips,
    pool_url="stratum+tcp://newpool.com:3333",
    worker_name="newuser.fleet",
    pool_password="x",
    initiated_by="admin"
)

print(f"Migrated {results['successful']} miners to new pool")
```

### 3. Cost-Optimized Power Schedule
```python
# Create schedule that aligns with TOU electricity rates
# Turn off during peak hours (5-9 PM weekdays)
schedule = PowerScheduleService.create_schedule(
    session,
    name="TOU Optimization",
    description="Shutdown during peak electricity hours",
    schedule_type="weekly",
    weekly_schedule=[
        {
            "day": 0,  # Monday
            "start_hour": 17,
            "end_hour": 21,
            "action": "off"
        },
        {
            "day": 1,  # Tuesday
            "start_hour": 17,
            "end_hour": 21,
            "action": "off"
        },
        # ... repeat for Wed, Thu, Fri
    ],
    electricity_rate_id=1,  # Link to TOU rate
    enabled=True
)

# Potential savings: 30-50% on electricity costs!
```

### 4. Pre-Update Backup
```python
# Backup all miners before firmware update
for miner_ip in miner_ips:
    backup = RemoteControlService.backup_config(
        session,
        miner_ip,
        backup_name=f"Pre-firmware-v2.0",
        description="Backup before firmware update to v2.0",
        created_by="admin"
    )
    print(f"Backed up {miner_ip}: {backup.id}")
```

## Best Practices

### 1. Always Backup Before Changes
```python
# Best practice: backup before pool switch or firmware update
backup = RemoteControlService.backup_config(session, miner_ip, ...)
RemoteControlService.switch_pool(session, miner_ip, ...)
```

### 2. Use Batch Operations Carefully
- Don't reboot entire fleet at once (impacts revenue)
- Stagger operations: reboot in groups of 10-20%
- Monitor command history for failures

### 3. Test Schedules First
- Create schedule for single miner first
- Verify behavior for 24-48 hours
- Then apply to fleet

### 4. Monitor Command History
- Check daily for failed commands
- Investigate timeouts (network issues?)
- Track which users execute which commands

### 5. Link Schedules to TOU Rates
- Always link power schedules to electricity rates
- Review profitability impact
- Adjust schedules based on actual savings

## Troubleshooting

### Issue: Reboot commands timing out
**Solutions:**
- Check network connectivity to miners
- Increase CGMiner timeout in config
- Verify miners are responding to API calls

### Issue: Pool switch not working
**Solutions:**
- Verify pool URL format (include port)
- Check worker name format
- Ensure miner firmware supports pool switching

### Issue: Backups failing
**Solutions:**
- Check disk space
- Verify miner API is accessible
- Review error messages in command history

### Issue: Schedule not executing
**Solutions:**
- Verify schedule is enabled
- Check timezone settings
- Ensure scheduler service is running
- Manually trigger with `/api/remote/schedule/check`

## Security Considerations

1. **Authentication Required**: All endpoints require login
2. **Audit Logging**: Every command is logged with user tracking
3. **Rate Limiting**: Consider implementing for production
4. **Backup Encryption**: Store sensitive configs securely
5. **Network Security**: Use VPN for remote access

## Integration with Scheduler

The power scheduling system integrates with the main application scheduler:

```python
# In scheduler.py
from core.remote_control import PowerScheduleService

def check_power_schedules():
    """Called every minute by scheduler"""
    session = SessionLocal()
    results = PowerScheduleService.check_and_execute_schedules(session)
    logger.info(f"Schedule check: {results}")
    session.close()

# Add to scheduler jobs
scheduler.add_job(
    check_power_schedules,
    'interval',
    minutes=1,
    id='power_schedule_check'
)
```

## Future Enhancements

Planned features:
- [ ] Firmware update automation
- [ ] Performance tuning (frequency/voltage)
- [ ] Fan control
- [ ] Configuration templates
- [ ] Scheduled backups
- [ ] Restore from backup
- [ ] Multi-pool load balancing
- [ ] Failover pool automation
- [ ] Temperature-based power limiting
- [ ] Geographic load distribution

---

**Version**: 1.0  
**Last Updated**: 2025-10-19  
**Author**: Mining Operations Team
