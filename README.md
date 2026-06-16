# 🔍 Job Scout

> A free, local-first job aggregator. Search LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google Jobs simultaneously — no accounts, no API keys, no data sent anywhere.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Powered by JobSpy](https://img.shields.io/badge/Powered%20by-JobSpy-orange.svg)](https://github.com/speedyapply/JobSpy)

---

## What's in this repo

| Path | What it is |
|---|---|
| [`job-scout/`](job-scout/) | Full web app — drag-and-drop CV, live search, filter/sort/export UI |
| [`job_scout.py`](job_scout.py) | Lightweight CLI script — configure once, run from terminal, outputs CSV + Markdown |

Both tools are built on [JobSpy](https://github.com/speedyapply/JobSpy) and run entirely on your machine.

---

## Web App — Quick Start

### macOS / Linux
```bash
git clone https://github.com/Jmx097/Job-Scout-public
cd Job-Scout-public/job-scout
chmod +x install.sh start.sh
./install.sh     # one-time setup
./start.sh       # opens http://localhost:5000
```

### Windows
```
git clone https://github.com/Jmx097/Job-Scout-public
cd Job-Scout-public\job-scout
install.bat
start.bat
```

> **No Python?** Build a standalone `.exe` / binary first — see [`job-scout/README.md`](job-scout/README.md#option-a--one-click-executable-recommended).

---

## Web App — Features

- **CV upload** — drag-and-drop PDF or DOCX; extracts skills and roles to pre-fill your search
- **Multi-source search** — LinkedIn · Indeed · Glassdoor · ZipRecruiter · Google Jobs (concurrent)
- **Company careers links** — links go directly to the company's `/careers` page, not ephemeral job-board URLs
- **Live progress stream** — real-time updates as each source responds via SSE
- **Filter & sort** — remote, full-time, has-salary, newest first
- **CSV export** — one-click download of all results
- **Proxy support** — configure rotating proxies in the Settings tab (recommended for LinkedIn)
- **100% local** — nothing leaves your machine

---

## CLI Script — Quick Start

```bash
pip install -U python-jobspy pandas
python job_scout.py
```

Edit the `CONFIG` block at the top of `job_scout.py` to set your search terms, salary floor, location, and filters. Outputs:

| File | Contents |
|---|---|
| `jobs_raw.csv` | Everything scraped — useful for debugging |
| `jobs_filtered.csv` | Filtered & scored matches |
| `shortlist.md` | Top picks with direct company careers-page links |

---

## Requirements

- Python 3.10 or later ([download](https://www.python.org/downloads/))
- Dependencies install automatically via `install.sh` / `install.bat` for the web app, or manually via `pip` for the CLI

---

## Architecture

```
Job-Scout-public/
├── job-scout/           # Web app
│   ├── app.py           # Flask backend — CV parsing, JobSpy wrapper, SSE streaming
│   ├── requirements.txt
│   ├── static/
│   │   └── index.html   # Single-file SPA — all CSS + JS inline
│   ├── uploads/         # Temporary CV storage (local only, gitignored)
│   ├── install.sh / install.bat / install.ps1
│   ├── start.sh / start.bat
│   └── build.sh / build.bat / build.ps1   # Compile to standalone binary
└── job_scout.py         # CLI script
```

---

## Proxy Setup (Recommended for LinkedIn)

LinkedIn rate-limits aggressively without proxies. Add proxies in the web app's **Settings** tab (one per line):

```
user:pass@host:port
```

For the CLI script, set the `PROXIES` list in the `CONFIG` block.

---

## Contributing

PRs and issues welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — see [LICENSE](LICENSE).

Built on [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy) · [Flask](https://flask.palletsprojects.com/)
