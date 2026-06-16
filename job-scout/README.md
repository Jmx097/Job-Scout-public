# 🔍 Job Scout

A local, open-source job aggregator with a polished UI. Upload your CV, set your criteria, and scout hot opportunities across LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google Jobs — all in one place.

Built with the [BMAD methodology](https://github.com/bmad-code-org/BMAD-METHOD) and powered by [JobSpy](https://github.com/speedyapply/JobSpy).

---

## Features

- **CV upload** — drag-and-drop PDF or DOCX; auto-extracts skills and roles to pre-fill your search
- **Multi-source search** — LinkedIn · Indeed · Glassdoor · ZipRecruiter · Google Jobs (concurrent)
- **Company careers links** — links go to the company's `/careers` page, not ephemeral listing URLs
- **Live progress stream** — real-time updates as each source responds
- **Filter & sort** — remote, full-time, has-salary, newest first
- **CSV export** — one click to export all results
- **Proxy support** — configure proxies in the Settings tab to avoid rate limits
- **100% local** — no accounts, no API keys, no data sent anywhere

---

## Requirements

- Python 3.10 or later ([download](https://www.python.org/downloads/))

---

## Quick Start

### Option A — One-click executable (recommended)

Build once, share anywhere. No Python required on the target machine.

**Windows:**
```
install.bat     ← sets up the build environment (once)
build.bat       ← compiles to dist\JobScout.exe (once)
```
Then double-click `dist\JobScout.exe` — browser opens automatically.

**macOS / Linux:**
```bash
chmod +x install.sh build.sh
./install.sh
./build.sh      # produces dist/JobScout (+ dist/JobScout.app on Mac)
```

### Option B — Run from source

**macOS / Linux:**
```bash
git clone https://github.com/Jmx097/scout
cd scout/job-scout
chmod +x install.sh start.sh
./install.sh
./start.sh
```

**Windows:**
```
git clone https://github.com/Jmx097/scout
cd scout\job-scout
install.bat
start.bat
```

Then open **http://localhost:5000** in your browser (it opens automatically).

---

## Usage

1. **CV tab** — upload your PDF or DOCX CV. Skills and roles are extracted automatically and used to pre-fill the search.
2. **CV tab / Criteria tab** — set your job title, location, remote preference, and job type.
3. Hit **Scout Jobs** — results stream in as each board responds.
4. **Filter** results by Remote / Full Time / Has Salary.
5. Click **Company Careers** on any card to go directly to that company's careers page.
6. Export to CSV if you want to track applications in a spreadsheet.

---

## Configuration

| Setting | Where | Default |
|---|---|---|
| Port | `PORT` env variable | `5000` |
| Results per source | Criteria panel | `15` |
| Posted within | Criteria panel | `72 hours` |
| Proxies | Settings panel | None |

### Proxies (recommended for LinkedIn)

LinkedIn rate-limits aggressively. Add proxies in the **Settings** tab (one per line):

```
user:pass@host:port
```

---

## Architecture

```
job-scout/
├── app.py           # Flask backend — CV parsing, JobSpy wrapper, SSE streaming
├── requirements.txt
├── install.sh / install.bat
├── start.sh / start.bat
├── static/
│   └── index.html   # Single-file SPA — all CSS + JS inline
└── uploads/         # Temporary CV storage (local only)
```

The backend exposes three endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/upload-cv` | POST | Parse CV, return keywords |
| `POST /api/search` | POST | Start a JobSpy search, return session ID |
| `GET /api/search/:id/stream` | GET (SSE) | Stream progress events |
| `GET /api/search/:id/results` | GET | Fetch final results |

---

## Notes on Job Sources

| Source | Notes |
|---|---|
| **Indeed** | Best results, no rate limiting, searches description text |
| **LinkedIn** | Richest data; rate-limits ~page 10 without proxies |
| **ZipRecruiter** | US/Canada only |
| **Google Jobs** | Requires specific `google_search_term` syntax |
| **Glassdoor** | Good coverage, opt-in |

---

## Open Source

MIT License. Contributions welcome — PRs, issues, and forks encouraged.

Built on top of:
- [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy) — the scraping engine
- [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) — agent-driven development methodology
- [Flask](https://flask.palletsprojects.com/) — backend framework
