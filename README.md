# TrafficWeaver v1.1

> Simulate realistic human download and browsing traffic — now with a full web dashboard.

---

## What It Does

TrafficWeaver generates outbound traffic that mimics real human behaviour:

- Downloads files from a configurable list, throttled to a realistic speed
- Randomly pauses mid-download and resumes (simulating someone walking away)
- Visits websites with a real or headless browser, follows internal links, and scrolls
- Distributes activity across the day following a natural curve (quiet at night, active during the day)
- Adds daily randomness to the total target so the traffic pattern is never identical

### What's New in v1.1

- **Web Dashboard** — full SPA with login, dark/light mode, real-time logs
- **TOML Configuration** — no more `.env` files; clean TOML-based config
- **SQLite Database** — persistent storage for sites, stats, and logs
- **Live Reload** — change settings from the UI without restarting
- **Simple & Advanced Modes** — simplified setup or full control over all parameters
- **REST API** — full programmatic control via HTTP endpoints
- **WebSocket Logs** — real-time log streaming to the browser

---

## Project Structure

```
trafficweaver/
├── main.py                          # Application entry point
├── config.default.toml              # Default configuration (copy to config.toml)
├── requirements.txt                 # Python dependencies
├── backend/
│   ├── api/
│   │   ├── app.py                   # FastAPI application factory
│   │   ├── auth.py                  # JWT authentication
│   │   └── routes.py                # REST + WebSocket endpoints
│   ├── core/
│   │   ├── config_manager.py        # TOML config loader with live-reload
│   │   ├── engine.py                # Traffic simulation orchestrator
│   │   ├── scheduler.py             # Human-activity-curve event scheduler
│   │   ├── downloader.py            # Async throttled file downloader
│   │   └── browser.py               # Site browsing (aiohttp / Playwright)
│   ├── db/
│   │   └── database.py              # SQLite ORM layer
│   └── utils/
│       └── log_handler.py           # Structured logging + WebSocket broadcast
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Root SPA component
│   │   ├── pages/                   # Dashboard, Settings, Logs, Sites
│   │   ├── components/              # Shared UI components
│   │   ├── hooks/                   # Auth, Theme, WebSocket hooks
│   │   └── lib/                     # API client, utilities
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── data/                            # SQLite database (auto-created)
└── logs/                            # Log files (auto-created)
```

---

## Quick Start

### 1. Clone & Configure

```bash
https://github.com/enavid/trafficweaver.gitgit clone <repository-url>
cd trafficweaver
cp config.default.toml config.toml
# Edit config.toml if needed (or configure everything via the UI)
```

### 2. Install Python Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Build the Frontend (first time only)

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Run

```bash
python main.py
```

Open **http://localhost:8099** in your browser.

Default credentials:

- Username: `admin`
- Password: `admin`

> Change the password after first login via Settings.

---

## Configuration (`config.toml`)

All settings are managed through a single TOML file. Settings can also be changed live through the web UI.

```toml
[server]
host = "0.0.0.0"
port = 8099
secret_key = "change-me-in-production"

[auth]
username = "admin"
password_hash = "..."

[traffic]
daily_target_bytes = 10737418240    # 10 GB
daily_variance = 0.20               # +/-20%

[traffic.schedule]
weights = [0.05, 0.30, 0.35, 0.30]  # [00-06, 06-12, 12-18, 18-24]

[traffic.download]
max_concurrent = 2
speed_cap_bps = 2097152             # 2 MB/s (0 = unlimited)
pause_probability = 0.3
pause_range = [15, 120]             # seconds

[traffic.browsing]
delay_range = [8, 75]               # seconds between visits
max_internal_links = 3
use_playwright = false

[network]
bind_ip = ""                        # empty = default interface

[logging]
level = "INFO"
file = "logs/trafficweaver.log"
```

---

## Web Dashboard

The dashboard provides:

| Page                     | Features                                                 |
| ------------------------ | -------------------------------------------------------- |
| **Dashboard**      | Engine status, daily stats, progress bar, traffic chart  |
| **Download Sites** | Add/remove/toggle download URLs with file sizes          |
| **Browsing Sites** | Add/remove/toggle browsing URLs                          |
| **System Logs**    | Real-time log stream (WebSocket), level filters, history |
| **Settings**       | Simple/Advanced mode, all config, password change        |

### Simple vs Advanced Mode

- **Simple** — Set daily target (GB), speed cap (MB/s), concurrent downloads, and browser engine
- **Advanced** — Full control: variance, schedule weights, pause probability/range, browsing delays, bind IP, log level

All changes apply immediately without restart.

---

## API Reference

All endpoints require authentication via `Bearer` token (obtained from `/api/auth/login`).

| Method | Endpoint                      | Description                        |
| ------ | ----------------------------- | ---------------------------------- |
| POST   | `/api/auth/login`           | Authenticate and receive JWT token |
| POST   | `/api/auth/change-password` | Change the user password           |
| GET    | `/api/config`               | Get current configuration          |
| PATCH  | `/api/config`               | Update configuration (live reload) |
| GET    | `/api/engine/status`        | Engine running state               |
| POST   | `/api/engine/start`         | Start the traffic engine           |
| POST   | `/api/engine/stop`          | Stop the traffic engine            |
| GET    | `/api/download-sites`       | List all download sites            |
| POST   | `/api/download-sites`       | Add a download site                |
| PATCH  | `/api/download-sites/:id`   | Update a download site             |
| DELETE | `/api/download-sites/:id`   | Delete a download site             |
| GET    | `/api/browsing-sites`       | List all browsing sites            |
| POST   | `/api/browsing-sites`       | Add a browsing site                |
| PATCH  | `/api/browsing-sites/:id`   | Update a browsing site             |
| DELETE | `/api/browsing-sites/:id`   | Delete a browsing site             |
| GET    | `/api/stats/today`          | Today's traffic statistics         |
| GET    | `/api/stats/history`        | Historical daily stats             |
| GET    | `/api/logs`                 | Query log entries                  |
| DELETE | `/api/logs`                 | Clear all logs                     |
| WS     | `/api/ws/logs?token=...`    | Real-time log stream (WebSocket)   |

---

## Binding to a Specific Network Interface

If your machine has multiple network interfaces (e.g. Starlink + local ISP), set `bind_ip` to the IP address of the desired interface:

```toml
[network]
bind_ip = "192.168.x.x"
```

Or configure it through the Settings page (Advanced mode) in the web UI.

---

## Optional: Playwright (Real Browser)

Set `use_playwright = true` in `config.toml` or toggle it in the Settings page, then install Chromium:

```bash
playwright install chromium
```

This makes browsing simulation significantly harder to fingerprint as automated traffic.

---

## Autorun

### Linux — systemd

```ini
# /etc/systemd/system/trafficweaver.service
[Unit]
Description=TrafficWeaver traffic simulator
After=network-online.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/trafficweaver
ExecStart=/path/to/trafficweaver/.venv/bin/python main.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now trafficweaver
```

### Windows — Task Scheduler

1. Open **Task Scheduler** → Create Basic Task
2. Trigger: At system startup
3. Action: Start a program → `python main.py` in the project directory
4. Check "Run whether user is logged on or not"

---

## Frontend Development

To develop the frontend with hot-reload:

```bash
# Terminal 1: Start the backend
python main.py

# Terminal 2: Start the Vite dev server
cd frontend
npm run dev
```

The Vite dev server (port 3000) proxies API requests to the backend (port 8099).

---

## Tech Stack

| Component | Technology                               |
| --------- | ---------------------------------------- |
| Backend   | Python 3.10+, FastAPI, Uvicorn, SQLite   |
| Frontend  | React 18, TypeScript, Vite, Tailwind CSS |
| Config    | TOML                                     |
| Auth      | JWT (HMAC-SHA256)                        |
| Real-time | WebSocket                                |
| Charts    | Recharts                                 |
| Icons     | Lucide React                             |

---

## License

MIT
