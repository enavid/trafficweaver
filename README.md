# TrafficWeaver

> Simulate realistic human download traffic across 24 hours – configurable, cross-platform, bot-resistant.

---

## What it does

TrafficWeaver generates outbound download traffic that mimics real human behaviour:

- Downloads files from a configurable list, throttled to a humanly reasonable speed.
- Randomly pauses mid-download and resumes (like someone who walked away).
- Visits websites with a real or headless browser, follows a few internal links, and scrolls.
- Distributes all activity across the day following a natural activity curve (quiet at night, active morning/evening).
- Adds ±20% daily randomness to the total target so the traffic pattern is never identical day-to-day.
- Asks how many days to run on startup — enter `0` to run forever.

---

## Project Structure

```
trafficweaver/
├── main.py                  # Orchestrator & entry point
├── requirements.txt
├── .env.example
├── src/
│   ├── __init__.py
│   ├── config.py            # .env loader & dataclasses
│   ├── scheduler.py         # Human-activity-curve event scheduler
│   ├── downloader.py        # Async throttled file downloader
│   ├── browser.py           # Site browsing (aiohttp or Playwright)
│   ├── stats.py             # Daily progress tracker
│   └── logger.py            # Structured rotating logger
├── script/
│   ├── run_linux.sh         # Linux/macOS one-click launcher
│   └── run_windows.bat      # Windows one-click launcher
└── logs/
    ├── trafficweaver.log
    └── daily_stats.json
```

---

## Quick Start

### 1 · Clone & configure

```bash
git clone https://github.com/enavid/trafficweaver.git
cd trafficweaver
cp .env.example .env
# Edit .env with your preferred editor
```

### 2 · Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 3 · Run

```bash
python main.py
```

On startup it will ask:
```
How many days to run? (0 = run forever):
```

Enter a number or `0` to run indefinitely. Each 24-hour cycle completes and restarts automatically.

---

## Configuration (`.env`)

> List values (FILE_DOWNLOAD_LIST, BROWSING_SITE_LIST) use **comma-separated** entries on a single line.

| Variable | Default | Description |
|---|---|---|
| `DAILY_TARGET_BYTES` | `10737418240` (10 GB) | Daily download target in bytes |
| `DAILY_VARIANCE` | `0.20` | ±% randomness applied to the daily target |
| `FILE_DOWNLOAD_LIST` | see example | `URL\|SIZE_BYTES` pairs, comma-separated |
| `BROWSING_SITE_LIST` | see example | URLs to browse, comma-separated |
| `SCHEDULE_WEIGHTS` | `0.05,0.30,0.35,0.30` | Activity weight per 6-hour window `[00-06, 06-12, 12-18, 18-24]` |
| `MAX_CONCURRENT_DOWNLOADS` | `2` | Parallel downloads |
| `DOWNLOAD_SPEED_CAP` | `2097152` (2 MB/s) | Per-file speed cap in bytes/sec; `0` = unlimited |
| `DOWNLOAD_PAUSE_PROBABILITY` | `0.3` | Chance of a random mid-download pause |
| `DOWNLOAD_PAUSE_RANGE` | `15,120` | Pause duration range in seconds |
| `BROWSE_DELAY_RANGE` | `8,75` | Seconds between page visits |
| `BROWSE_MAX_INTERNAL_LINKS` | `3` | Internal links to follow per site |
| `USE_PLAYWRIGHT` | `False` | Use real Chromium (harder to detect as bot) |
| `BIND_IP` | _(empty)_ | Bind outbound traffic to a specific network interface IP |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `LOG_FILE` | `logs/trafficweaver.log` | Log file path |

### Example `.env` list format

```env
FILE_DOWNLOAD_LIST=https://speed.hetzner.de/100MB.bin|104857600,https://speed.hetzner.de/1GB.bin|1073741824

BROWSING_SITE_LIST=https://www.wikipedia.org,https://www.github.com,https://www.stackoverflow.com
```

### Binding to a specific network interface

If your machine has multiple network interfaces (e.g. Starlink + local ISP), set `BIND_IP` to the IP address of the interface you want TrafficWeaver to use:

```env
BIND_IP=192.168.x.x
```

All outbound traffic from TrafficWeaver will go through that interface — no OS-level routing rules needed.

---

## Optional: Playwright (real browser)

Set `USE_PLAYWRIGHT=True` in `.env`, then run once:

```bash
playwright install chromium
```

This makes the browsing simulation significantly harder to fingerprint as automated traffic.

---

## Autorun

### Windows – Task Scheduler

1. Open **Task Scheduler** → *Create Basic Task*
2. Trigger: **At system startup**
3. Action: **Start a program** → browse to `script\run_windows.bat`
4. Check *Run whether user is logged on or not*
5. Check *Run with highest privileges*

### Linux – systemd

```ini
# /etc/systemd/system/trafficweaver.service
[Unit]
Description=TrafficWeaver download simulator
After=network-online.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/trafficweaver
ExecStart=/path/to/trafficweaver/.venv/bin/python main.py
StandardInput=null
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now trafficweaver
sudo systemctl status trafficweaver
```

### Linux – cron (simpler alternative)

```bash
@reboot /path/to/trafficweaver/script/run_linux.sh >> /var/log/trafficweaver.log 2>&1
```

---

## Logs

All activity is logged to `logs/trafficweaver.log` (rotating, 10 MB × 5 files) and to stdout.
Daily statistics are persisted in `logs/daily_stats.json` and survive restarts within the same day.