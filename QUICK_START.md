# Quick Start: Trimmer Online Status

## What Was Changed

### 1. Added Heartbeat Function to Database Layer
**File**: `src/connectvision/database.py`
- New method: `heartbeat(machine_id)` 
- Updates `secondary_machines.last_seen = NOW()`

### 2. Updated Trimmer Monitor Script  
**File**: `scripts/trimmer_monitor_v2.py`
- Sends initial heartbeat on startup → Machine appears ONLINE immediately
- Sends heartbeat every 10 seconds → Keeps machine ONLINE
- Logs heartbeat status to console

### 3. Updated Dashboard API
**File**: `htdocs/SECONDARY/api/get_trimmers_telemetry.php`
- Reduced online threshold from 5 minutes → 30 seconds
- Single source of truth: `secondary_machines.last_seen`

### 4. Dashboard Already Working
**File**: `htdocs/SECONDARY/TrimmingDashboard.php`
- No changes needed - already reads from API correctly
- Shows Online/Offline badge based on heartbeat

## How to Use

### Start a Trimmer Monitor
```bash
python3 trimmer_monitor_v2.py --machine-id 14
```

**Expected Output**:
```
[12:34:56] ✓ Initial heartbeat sent - machine 14 is ONLINE
Trimmer Monitor with Web Interface
Machine: Trimmer 1 (ID: 14)
Web Interface: http://192.168.1.101:8080
Press Ctrl+C to stop
```

### Check Dashboard
1. Open `TrimmingDashboard.php` in browser
2. Within 10 seconds, Trimmer 14 should show:
   - ✅ **Online** badge (green dot)
   - ✅ Green card border
   - ✅ Counted in "Online" fleet metric

### Stop the Monitor
```bash
# Press Ctrl+C
^C
Stopping trimmer monitor for machine 14
Machine will appear OFFLINE in dashboard after 30 seconds
```

Dashboard will show **Offline** within 30 seconds.

## Testing Checklist

- [ ] Start trimmer script - see "Initial heartbeat sent" message
- [ ] Dashboard shows trimmer ONLINE within 10 seconds
- [ ] Stop script - dashboard shows OFFLINE within 30 seconds
- [ ] Restart script - dashboard shows ONLINE again within 10 seconds

## Timing Summary

| Event | Time |
|-------|------|
| Script starts → ONLINE | ~10 seconds |
| Script stops → OFFLINE | ~30 seconds |
| Heartbeat interval | 10 seconds |
| Dashboard poll | 5 seconds |

## What's Next?

1. Deploy `trimmer_monitor_v2.py` to all Raspberry Pi units
2. Configure each to start on boot with correct `--machine-id`
3. Monitor dashboard to verify all trimmers appear ONLINE
4. Test stopping/starting scripts to verify offline detection

## Files to Deploy

```
connectVision/
├── src/connectvision/database.py         ← Updated with heartbeat()
└── scripts/trimmer_monitor_v2.py         ← Updated with heartbeat logic

htdocs/SECONDARY/
├── api/get_trimmers_telemetry.php        ← Updated online threshold
└── TrimmingDashboard.php                 ← No changes needed
```

## Support

See `TRIMMER_ONLINE_STATUS_INTEGRATION.md` for full documentation and troubleshooting.
