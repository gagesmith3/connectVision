# Deployment Checklist - Trimmer Online Status Integration

## Pre-Deployment Verification

### Database
- [ ] Verify `secondary_machines` table exists in `iwt_db`
- [ ] Verify all trimmer machines (ID 14-25) exist in table
- [ ] Check `last_seen` column exists (should be TIMESTAMP type)

```sql
-- Verify table structure
DESCRIBE iwt_db.secondary_machines;

-- Check existing trimmers
SELECT machineID, machineName, processType, last_seen 
FROM iwt_db.secondary_machines 
WHERE processType = 'TRIM' 
ORDER BY machineID;
```

### Code Updates
- [ ] Updated files deployed to network share:
  - `\\192.168.1.6\int_pc_data\connectVision\src\connectvision\database.py`
  - `\\192.168.1.6\int_pc_data\connectVision\scripts\trimmer_monitor_v2.py`
  - `\\192.168.1.6\int_pc_data\xampp\htdocs\SECONDARY\api\get_trimmers_telemetry.php`

## Deployment Steps

### Step 1: Test on One Trimmer First
- [ ] Choose test trimmer (e.g., Trimmer 14)
- [ ] SSH/access Raspberry Pi for that trimmer
- [ ] Update code on Pi:
```bash
cd /home/pi/connectVision
git pull  # or manually copy updated files
```

- [ ] Start monitor script:
```bash
python3 scripts/trimmer_monitor_v2.py --machine-id 14
```

- [ ] Verify console output shows:
```
[HH:MM:SS] ✓ Initial heartbeat sent - machine 14 is ONLINE
```

### Step 2: Verify Dashboard
- [ ] Open `TrimmingDashboard.php` in browser
- [ ] Wait up to 10 seconds
- [ ] Verify Trimmer 14 shows:
  - Green "Online" badge
  - Green card border
  - Appears in "Online" count

### Step 3: Test Offline Detection
- [ ] Stop the test trimmer script (Ctrl+C)
- [ ] Wait 30-35 seconds
- [ ] Verify dashboard shows:
  - Red "Offline" badge
  - Gray card border
  - Removed from "Online" count

### Step 4: Test Restart
- [ ] Restart trimmer script
- [ ] Wait 10 seconds
- [ ] Verify shows ONLINE again

### Step 5: Deploy to Remaining Trimmers
- [ ] For each remaining trimmer (15-25):
  - Update code on Pi
  - Configure systemd service (if auto-start desired)
  - Start monitor script with correct `--machine-id`
  - Verify appears ONLINE in dashboard

## Systemd Service Configuration (Optional)

Create `/etc/systemd/system/trimmer-monitor.service` on each Pi:

```ini
[Unit]
Description=Trimmer Monitor with Vision Detection
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/connectVision
ExecStart=/usr/bin/python3 /home/pi/connectVision/scripts/trimmer_monitor_v2.py --machine-id 14
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Note**: Change `--machine-id 14` to match each trimmer's actual ID

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trimmer-monitor
sudo systemctl start trimmer-monitor
sudo systemctl status trimmer-monitor
```

View logs:
```bash
sudo journalctl -u trimmer-monitor -f
```

## Post-Deployment Verification

### Check All Trimmers Online
- [ ] Open dashboard
- [ ] Verify all deployed trimmers show ONLINE
- [ ] Check "Fleet Badges" show correct counts

### Database Health Check
```sql
-- View all trimmer heartbeats
SELECT 
    machineID, 
    machineName,
    last_seen,
    TIMESTAMPDIFF(SECOND, last_seen, NOW()) AS seconds_ago
FROM secondary_machines 
WHERE processType = 'TRIM'
ORDER BY machineID;
```

Expected results:
- All deployed trimmers: `seconds_ago` between 0-10
- Not yet deployed: `seconds_ago` > 30 or NULL

### Monitor for 1 Hour
- [ ] Check dashboard every 5-10 minutes
- [ ] Verify trimmers stay ONLINE consistently
- [ ] Check for any flapping (ONLINE ↔ OFFLINE repeatedly)
- [ ] Review Pi logs for heartbeat errors

## Troubleshooting Guide

### Trimmer Shows Offline Despite Script Running

**Check Script Logs**:
```bash
sudo journalctl -u trimmer-monitor -n 50
```

Look for:
- ✗ WARNING: Heartbeat failed
- Database connection errors
- Network errors

**Check Database**:
```sql
SELECT machineID, last_seen 
FROM secondary_machines 
WHERE machineID = 14;
```

If `last_seen` is not updating:
1. Verify database credentials in script
2. Check network connectivity: `ping 192.168.1.6`
3. Verify machineID exists in table

### Dashboard Not Updating

**Check Browser Console** (F12):
- Look for JavaScript errors
- Check Network tab for API calls
- Verify `get_trimmers_telemetry.php` returns JSON

**Test API Directly**:
```bash
curl http://192.168.1.6/SECONDARY/api/get_trimmers_telemetry.php
```

Should return JSON array with all trimmers.

### Heartbeat Keeps Failing

**Common Causes**:
1. **MySQL Connection Lost**: Check network, restart MySQL
2. **Credentials Wrong**: Verify `webapp`/`STUDS2650` in script
3. **Table Missing**: Verify `secondary_machines` exists
4. **Wrong Machine ID**: Verify ID exists in table

**Fix**:
```bash
# On Pi, test database connection
python3 << EOF
from connectvision.database import ConnectVisionDB, MySQLConfig

config = MySQLConfig(
    host='192.168.1.6',
    port=3306,
    user='webapp',
    password='STUDS2650',
    database='iwt_db'
)
db = ConnectVisionDB(config)
result = db.heartbeat(14)
print(f"Heartbeat test: {'SUCCESS' if result else 'FAILED'}")
db.close()
EOF
```

## Rollback Plan

If issues occur, rollback by:

1. **Stop All Trimmer Scripts**:
```bash
# On each Pi
sudo systemctl stop trimmer-monitor
```

2. **Revert API File**:
```bash
# Restore previous version of get_trimmers_telemetry.php
# Change online threshold back to 300 seconds
```

3. **Dashboard Will Work** (just with longer offline delay)

## Success Criteria

- [ ] All deployed trimmers show ONLINE within 10 seconds of script start
- [ ] Trimmers show OFFLINE within 30 seconds of script stop
- [ ] No console errors in browser developer tools
- [ ] No heartbeat failures in Pi logs
- [ ] Fleet badges show accurate counts
- [ ] No database performance issues

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| QA/Tester | | | |
| Operations | | | |

## Notes

---
