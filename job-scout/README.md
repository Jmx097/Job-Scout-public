# Job Scout

A local, open-source job aggregator with a polished UI. Upload your CV, set your criteria, and scout opportunities across LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google Jobs in one place.

Built with the [BMAD methodology](https://github.com/bmad-code-org/BMAD-METHOD) and powered by [JobSpy](https://github.com/speedyapply/JobSpy).

## Features

- CV upload with PDF, DOCX, DOC, and TXT support
- Resume keyword extraction to pre-fill likely target roles
- Multi-source search across major job boards
- Fit scoring with stronger weighting for true title alignment
- Filters for remote, full-time, salary visibility, and freshness
- CSV export for application tracking
- Proxy support for sources that rate-limit aggressively
- 100% local runtime with no account or API key required

## Privacy

- The app runs locally on `127.0.0.1` by default.
- Uploaded CVs are parsed and then immediately deleted from disk.
- No resume data is intentionally sent to any third-party API by this app itself.
- Job searches do reach the selected job sources through JobSpy, so users should review the source terms and their own proxy setup before heavy use.

## Requirements

- Python 3.10 or later

## Quick Start

### Option A: Build a desktop executable

Windows:

```powershell
install.bat
build.bat
```

This produces `dist\JobScout.exe`.

macOS / Linux:

```bash
chmod +x install.sh build.sh
./install.sh
./build.sh
```

This produces `dist/JobScout` and, on macOS, `dist/JobScout.app`.

### Option B: Run from source

macOS / Linux:

```bash
git clone https://github.com/Jmx097/Job-Scout-public.git
cd Job-Scout-public/job-scout
chmod +x install.sh start.sh
./install.sh
./start.sh
```

Windows:

```powershell
git clone https://github.com/Jmx097/Job-Scout-public.git
cd Job-Scout-public\job-scout
install.bat
start.bat
```

Then open [http://localhost:5000](http://localhost:5000).

## Usage

1. Upload a CV in the CV tab.
2. Review the suggested role and adjust search criteria.
3. Choose location, remote preference, job type, freshness, and sources.
4. Run the search and review results sorted by best fit.
5. Export matching jobs to CSV if needed.

## Configuration

| Setting | Where | Default |
|---|---|---|
| Port | `PORT` env variable | `5000` |
| Results per source | Criteria panel | `15` |
| Posted within | Criteria panel | `72 hours` |
| Minimum fit | Criteria panel | `50` |
| Proxies | Settings panel | None |

Example proxy format:

```text
user:pass@host:port
```

## Architecture

```text
job-scout/
|-- app.py
|-- requirements.txt
|-- install.sh / install.bat
|-- start.sh / start.bat
|-- static/
|   `-- index.html
`-- uploads/
```

API endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/upload-cv` | POST | Parse CV and return extracted keywords |
| `/api/search` | POST | Start a search session |
| `/api/search/<id>/stream` | GET | Stream progress events |
| `/api/search/<id>/results` | GET | Fetch final results |

## Notes on Sources

- Indeed usually gives the broadest coverage.
- LinkedIn often benefits from proxies because of rate limiting.
- ZipRecruiter is strongest in the US and Canada.
- Google Jobs can benefit from a custom `google_search_term`.
- Glassdoor is optional and may add useful coverage.

## Distribution

This repository is intended to be cloned, modified, and self-hosted locally by other users. If you distribute binaries, keep the app bound to localhost unless you also add authentication, rate limits, and stronger file-handling controls.

## License

MIT. See [LICENSE](LICENSE).
