<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=220&section=header&text=GTU%20Academic%20Engine&fontSize=52&fontColor=ffffff&fontAlignY=38&desc=V2%20%E2%80%94%20The%20Unified%20Academic%20Resource%20Engine%20for%20Gujarat%20Technological%20University&descAlignY=60&descSize=16&animation=fadeIn" width="100%"/>

<br/>

<img src="https://readme-typing-svg.demolab.com?font=Outfit&weight=700&size=20&duration=2800&pause=900&color=A855F7&center=true&vCenter=true&width=700&lines=🔍+Live+cascading+GTU+portal+queries;⚡+2–4s+scraping+with+optimised+Playwright;📄+On-demand+PYQ+download+%26+PDF+merge+pipeline;💾+Local-first+cache+with+instant+fuzzy+search;🌐+Glassmorphic+dark-mode+web+dashboard" alt="Feature ticker"/>

<br/><br/>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-A855F7?style=for-the-badge)](LICENSE)
[![GTU](https://img.shields.io/badge/University-GTU%20Affiliated-F97316?style=for-the-badge)](https://www.gtu.ac.in)
[![Version](https://img.shields.io/badge/Version-2.0.0-22C55E?style=for-the-badge)](https://github.com/Nishit3116/GTU)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-0EA5E9?style=for-the-badge)](https://github.com/Nishit3116/GTU)

<br/>

> **An automated, local-first academic resource engine for GTU students.**
> Discover subjects, preview syllabi, and compile previous year question papers — all from a sleek dark-mode web dashboard, without ever touching the GTU portal manually.

<br/>

**[🚀 Quick Start](#%EF%B8%8F-installation)** &nbsp;|&nbsp; **[📖 How It Works](#-how-it-works)** &nbsp;|&nbsp; **[🌐 Deploy](#-cloud-deployment)** &nbsp;|&nbsp; **[⚙️ Configuration](#%EF%B8%8F-configuration)** &nbsp;|&nbsp; **[🤝 Contributing](#-contributing)**

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Installation](#%EF%B8%8F-installation)
- [Web Dashboard](#-web-dashboard)
- [Cloud Deployment](#-cloud-deployment)
- [Configuration](#%EF%B8%8F-configuration)
- [Running Tests](#-running-tests)
- [Contributing](#-contributing)
- [FAQ](#-faq)
- [License & Credits](#-license--credits)

---

## 🎯 Overview

GTU Academic Engine V2 is a **self-hosted web application** that automates the discovery and download of academic resources from [Gujarat Technological University](https://www.gtu.ac.in/).

Instead of manually navigating GTU's complex ASPX portal to find subject codes, syllabi, and question papers, this engine provides a **unified, fast, and beautiful web interface** powered by an intelligent scraping pipeline and a local cache system.

**Built for GTU students, by a GTU student.**

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **🔍 Smart Cascading Queries** | Live dropdowns: Course → Branch → Semester → Academic Year → Subject, all pulled in real-time from GTU's portal |
| **⚡ Optimised Scraping** | Playwright-based provider that reuses browser sessions, cutting query time from **15–20s → 2–4s** |
| **📄 PYQ Download Pipeline** | On-demand PDF downloads merged into a single compiled paper set; configure year range, sort order & session priority |
| **📋 Inline Syllabus Viewer** | Preview and download the official GTU syllabus directly in the browser — no external navigation |
| **💾 Local JSON Cache** | Full GTU course catalog cached in `gtu_academic_data.json` for near-instant fuzzy subject search |
| **🎨 Glassmorphic UI** | Dark-mode dashboard with micro-animations, gradient accents, animated typewriter header, and inline policy modals |
| **🔒 Fully Self-Hosted** | No third-party data sharing. Runs entirely on your machine or your own cloud server |
| **📦 pip-installable** | Clean `pyproject.toml` setup — install all dependencies with a single `pip install -e .` |

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | HTML5, Vanilla CSS, Vanilla JS | Glassmorphic web dashboard |
| **Backend** | Python 3.10+, Custom HTTP server | REST API serving the frontend |
| **Scraper** | [Playwright](https://playwright.dev/) (Chromium) | Headless interaction with GTU's ASPX portal |
| **PDF Engine** | [pypdf](https://github.com/py-pdf/pypdf) | Download validation & multi-PDF merge |
| **HTTP Client** | [requests](https://docs.python-requests.org/) | Resilient PDF fetching with retry logic |
| **Cache** | JSON (local file) | Zero-dependency fast subject lookup |
| **Packaging** | [setuptools](https://setuptools.pypa.io/) + `pyproject.toml` | Standard pip-installable package |
| **Formatting** | [black](https://black.readthedocs.io/) + [isort](https://pycqa.github.io/isort/) | Consistent code style |

---

## 🗂 Project Structure

```
GTU/
│
├── gtu_academic_engine/          # ── Core V2 Engine Package ──
│   ├── __init__.py
│   ├── __main__.py               # Entry point: python -m gtu_academic_engine
│   ├── server.py                 # Custom Python HTTP server (port 5000)
│   │
│   ├── provider/
│   │   └── aspx_provider.py     # 🕷️  Playwright scraper for GTU's ASPX portal
│   │
│   ├── cache/
│   │   ├── cache_manager.py     # Reads/writes gtu_academic_data.json
│   │   └── gtu_academic_data.json  # Local course catalog cache
│   │
│   ├── metadata/
│   │   └── metadata_manager.py  # Download telemetry & report generation
│   │
│   └── web/                     # ── Frontend ──
│       ├── index.html           # Single-page app shell
│       ├── index.css            # Glassmorphic dark-mode stylesheet
│       └── index.js             # State management, API calls, typewriter
│
├── gtu_pyq_downloader/          # ── V1 Core Downloader (dependency) ──
│   ├── cli.py                   # CLI entry point (gtu-pyq command)
│   └── services/
│       ├── downloader.py        # Resilient HTTP downloader with retry/backoff
│       ├── merger.py            # pypdf-based multi-PDF merger
│       ├── pdf_validation.py    # PDF integrity checker (format, pages, encryption)
│       └── pipeline.py          # Orchestrator: download → validate → merge
│
├── tests/                       # Integration & unit tests
│
├── .github/workflows/ci.yml     # GitHub Actions CI workflow
├── pyproject.toml               # Package metadata & CLI scripts
├── LICENSE                      # MIT License
└── README.md
```

---

## 🔄 How It Works

```
┌──────────────┐     HTTP Request     ┌─────────────────────────┐
│  Browser UI  │ ──────────────────► │  Python API Server      │
│  (port 5000) │                      │  server.py              │
└──────────────┘                      └────────────┬────────────┘
                                                   │
                            ┌──────────────────────┼─────────────────────┐
                            ▼                      ▼                     ▼
                   ┌────────────────┐   ┌──────────────────┐   ┌─────────────────┐
                   │  Cache Manager │   │  ASPX Provider   │   │  Download       │
                   │  (JSON, fast)  │   │  (Playwright)    │   │  Pipeline       │
                   └────────────────┘   └────────┬─────────┘   └────────┬────────┘
                            │                    │                      │
                            │             GTU Portal              PDF Files
                            │           (gtu.ac.in)            (merged + validated)
                            │
                    gtu_academic_data.json
```

**Request lifecycle:**
1. **User** selects Course / Branch / Semester in the browser UI.
2. **Server** checks the JSON cache first — if a cache hit, returns instantly.
3. On a cache miss, the **ASPX Provider** launches a headless Chromium browser, submits the GTU portal form, and parses the response.
4. Results are saved to the cache and returned to the browser.
5. When downloading PYQs, the **Download Pipeline** fetches, validates, and merges PDFs into one file.

---

## ⚙️ Installation

### Prerequisites

| Requirement | Version |
|---|---|
| Python | `>= 3.10` |
| Git | any recent version |
| Internet | required for live GTU scraping |

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Nishit3116/GTU.git
cd GTU
```

---

### Step 2 — Create a Virtual Environment

```bash
python -m venv venv
```

**Activate it:**

```bash
# Windows (PowerShell)
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

---

### Step 3 — Install the Package

```bash
pip install -e .
```

> This installs all dependencies (`requests`, `pypdf`, `playwright`, `openpyxl`) and registers the `gtu-engine` and `gtu-pyq` terminal commands.

---

### Step 4 — Install Headless Browser

```bash
playwright install --with-deps chromium
```

> Required for the ASPX scraper to interact with GTU's portal. Only needs to be run once.

---

### Step 5 — Launch the Server

```bash
python -m gtu_academic_engine
```

Expected output:
```
INFO | Web application server running on http://localhost:5000
INFO | Loaded cache gtu_academic_data.json
```

Open **[http://localhost:5000/](http://localhost:5000/)** in any modern browser. ✅

---

## 🖥 Web Dashboard

The web interface is a single-page application with the following panels:

| Panel | Description |
|---|---|
| **Header** | Animated typewriter cycling through key features |
| **Quick Search** | Instant fuzzy search across all cached subjects by name or code |
| **Syllabus Portal** | Cascading dropdowns: Course → Branch → Semester → Academic Year → Elective Type |
| **Results Table** | Expandable subject rows with teaching scheme, max marks, credits, and action buttons |
| **PYQ Download Modal** | Year range picker, merge order, session preference (Winter-first / Summer-first) |
| **Syllabus Viewer** | Inline PDF iframe with one-click download — stays in the app |
| **Footer Modals** | Inline DMCA, Privacy Policy, Terms, Disclaimer, About, and Contact Us pages |

---

## 🌐 Cloud Deployment

> **For GTU students with the [GitHub Student Developer Pack](https://education.github.com/pack):**
> Claim **$200 free DigitalOcean credit** — enough to host this engine for years.

### Option A — DigitalOcean Droplet (Recommended)

**1. Claim your credit**

Visit [education.github.com/pack](https://education.github.com/pack) → find **DigitalOcean** → click **Get Access** and sign in with GitHub. The $200 credit is applied automatically.

**2. Create a Droplet**

| Setting | Value |
|---|---|
| Image | Ubuntu 22.04 LTS |
| Plan | Basic — $4/month (Shared CPU, 512 MB RAM) |
| Region | Bangalore `BLR1` or Singapore `SGP1` |
| Authentication | SSH Key (recommended) |

**3. Deploy the application**

```bash
# Connect to your server
ssh root@YOUR_DROPLET_IP

# Install system dependencies
sudo apt update && sudo apt install -y python3-pip python3-venv git

# Clone your repository
git clone https://github.com/Nishit3116/GTU.git
cd GTU

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Install headless browser (with system dependencies for Linux)
playwright install --with-deps chromium

# Start the server in the background
nohup python -m gtu_academic_engine > server.log 2>&1 &
echo "Server started. Logs: server.log"
```

**4. Get a free domain**

In the GitHub Student Pack, claim a free `.me` or `.tech` domain from **Namecheap**.
Add an **A Record** pointing `@` to your Droplet's IP address.

Your app will be live at `http://yourdomain.me:5000` 🎉

---

### Option B — Keep it Running (systemd service)

For a production-grade deployment that survives reboots:

```ini
# /etc/systemd/system/gtu-engine.service
[Unit]
Description=GTU Academic Engine V2
After=network.target

[Service]
User=root
WorkingDirectory=/root/GTU
ExecStart=/root/GTU/venv/bin/python -m gtu_academic_engine
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable gtu-engine
sudo systemctl start gtu-engine
sudo systemctl status gtu-engine
```

---

## ⚙️ Configuration

The engine uses `gtu_academic_engine/settings.json` for runtime configuration:

```json
{
  "retry_count": 3,
  "timeout_seconds": 15,
  "auto_merge": true,
  "default_merge_order": "ascending",
  "default_session_order": "winter-first",
  "parallel_downloads": 1
}
```

| Key | Type | Default | Description |
|---|---|---|---|
| `retry_count` | `int` | `3` | Number of HTTP retry attempts for each PDF download |
| `timeout_seconds` | `int` | `15` | Per-request HTTP timeout in seconds |
| `auto_merge` | `bool` | `true` | Automatically merge all downloaded PDFs into one file |
| `default_merge_order` | `string` | `ascending` | Year sort order: `ascending` or `descending` |
| `default_session_order` | `string` | `winter-first` | Session priority: `winter-first` or `summer-first` |
| `parallel_downloads` | `int` | `1` | Concurrent download threads (increase carefully) |

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

The test suite covers the session generator, URL builder, PDF validator, and merger modules.

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a branch** for your feature: `git checkout -b feature/my-feature`
3. **Make your changes** and follow the code style (`black` + `isort`)
4. **Run tests**: `python -m pytest tests/ -v`
5. **Open a Pull Request** with a clear description of what you changed and why

**Code style:**
```bash
pip install black isort
black .
isort .
```

---

## 🌐 Cloud Deployment

### Deploy on Render

The project includes a `render.yaml` file — connect your GitHub repository on [render.com](https://render.com) and click **Deploy**. No additional configuration required.

#### Build Command
```bash
pip install -e .
playwright install --with-deps chromium
```

#### Start Command
```bash
python -m gtu_academic_engine
```

#### How it works on Render

| What | Detail |
|---|---|
| **PORT** | Auto-injected by Render; the app reads `os.environ["PORT"]` |
| **Bind address** | `0.0.0.0` (all interfaces) — required for Render's proxy |
| **Playwright** | Chromium installed during build step; binary cached between deploys |
| **Health check** | `GET /health` returns `{"status":"OK","version":"2.0"}` |
| **Cache** | Stored on the ephemeral disk; refreshed via the web dashboard |

#### Supported Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5000` | HTTP server port (auto-set by Render) |
| `GTU_CACHE_PATH` | `<pkg>/cache` | Override cache directory |
| `GTU_DOWNLOAD_PATH` | `<pkg>/downloads` | Override downloads directory |
| `GTU_LOG_LEVEL` | `INFO` | Logging level: DEBUG / INFO / WARNING / ERROR |
| `GTU_METADATA_PATH` | `<pkg>/metadata` | Override metadata directory |

#### Startup Log (visible in Render dashboard)

```
================================================
  GTU Academic Engine V2.0
  Initializing...
  Loading Cache...  (empty — will scrape live)
  Initializing Playwright... OK
  Server Ready
  Listening on PORT: 10000
================================================
```

> **Note:** Free Render instances spin down after 15 minutes of inactivity. The first request after a cold start will take ~30 seconds (Playwright browser launch + GTU portal load). Subsequent requests are fast.

---

## ❓ FAQ

**Q: Does this store or upload my data anywhere?**
A: No. The engine is entirely self-hosted. The only external network requests are made directly to `gtu.ac.in` to fetch academic data.

**Q: Why does it need Playwright (a headless browser)?**
A: GTU's portal uses ASP.NET Web Forms with server-side session state (`__VIEWSTATE`). A regular HTTP request library cannot replicate this flow — a real browser session is required.

**Q: The scraper is slow on first load — is that normal?**
A: Yes. The first query must launch a Chromium browser session and interact with the GTU portal, which takes 2–4 seconds. All subsequent queries for the same data are served instantly from the local JSON cache.

**Q: Can I use this for branches other than Computer Engineering?**
A: Yes — the engine supports all GTU courses and branches. The cascading dropdowns expose every branch available on the portal.

**Q: The server crashed / an API returned an error. What should I check?**
A: Check the terminal output for the `gtu_academic_engine` process. Common causes: the GTU portal is down for maintenance, Playwright's Chromium binary was not installed correctly, or a network timeout occurred.

---


## 📜 License & Credits

<div align="center">

| | |
|---|---|
| **Developer** | [Nishit Savaliya](https://github.com/Nishit3116) |
| **Email** | [nishitsavaliya.me@gmail.com](mailto:nishitsavaliya.me@gmail.com) |
| **Repository** | [github.com/Nishit3116/GTU](https://github.com/Nishit3116/GTU) |
| **License** | MIT — see [LICENSE](LICENSE) for full text |

</div>

> **Disclaimer:** This is an unofficial, community-developed tool and is not affiliated with, endorsed by, or connected to Gujarat Technological University in any way. All academic materials including syllabi, question papers, and teaching schemes remain the intellectual property of GTU.

<div align="center">

<br/>

[![GitHub stars](https://img.shields.io/github/stars/Nishit3116/GTU?style=for-the-badge&logo=github&color=A855F7&label=Stars)](https://github.com/Nishit3116/GTU/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Nishit3116/GTU?style=for-the-badge&logo=github&color=6366F1&label=Forks)](https://github.com/Nishit3116/GTU/network)
[![GitHub issues](https://img.shields.io/github/issues/Nishit3116/GTU?style=for-the-badge&logo=github&color=F97316&label=Issues)](https://github.com/Nishit3116/GTU/issues)

<br/>

*If this project saved you time, please consider giving it a* ⭐ *— it helps others discover it.*

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=120&section=footer&animation=fadeIn" width="100%"/>

</div>
