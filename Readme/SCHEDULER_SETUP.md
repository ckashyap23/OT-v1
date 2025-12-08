# Daily Snapshot Scheduler Setup

The scheduler automatically runs `daily_intraday_stock_option.py` at:
- **9:20 AM IST**
- **3:20 PM IST (15:20 IST)**

## Automatic Startup Options

### Option 1: Windows Task Scheduler (Recommended)

This method runs the scheduler automatically at system startup, even if you're not logged in.

1. **Run the setup script** (as Administrator for best results):
   ```bash
   python scripts/setup_scheduler.py
   ```

2. The script will create a Windows Task Scheduler task that:
   - Runs at system startup
   - Keeps the scheduler running continuously
   - Executes the snapshot script at the scheduled times

3. **To remove the scheduled task**:
   ```bash
   python scripts/setup_scheduler.py --remove
   ```

**Note**: You may need to run the setup script as Administrator:
- Right-click on the script → "Run as administrator"

### Option 2: Windows Startup Folder (Simple)

This method runs the scheduler when you log in to Windows.

1. **Press `Win + R`** to open Run dialog
2. Type: `shell:startup` and press Enter
3. **Copy** `scripts/start_scheduler.bat` to the Startup folder
4. The scheduler will start automatically when you log in

### Option 3: Manual Start

If you prefer to start it manually:

```bash
python scripts/schedule_daily_snapshots.py
```

Press `Ctrl+C` to stop it.

## Verify It's Running

After setup, you can verify the scheduler is running by:

1. **Check Windows Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter
   - Look for task: `OT-v1_DailySnapshotScheduler`

2. **Check if Python process is running**:
   - Open Task Manager (`Ctrl + Shift + Esc`)
   - Look for `python.exe` running `schedule_daily_snapshots.py`

## Troubleshooting

- **Scheduler not starting**: Check Windows Task Scheduler for errors
- **Script not executing**: Verify Python path and dependencies are installed
- **Timezone issues**: The scheduler automatically converts IST to your local timezone
- **Permission errors**: Run setup script as Administrator

## Dependencies

Make sure these are installed:
```bash
pip install schedule pytz
```

