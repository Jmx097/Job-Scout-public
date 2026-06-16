# Contributing to Job Scout

Thanks for your interest! Contributions are welcome — bug reports, feature requests, and PRs.

## Getting started

```bash
git clone https://github.com/Jmx097/Job-Scout-public
cd Job-Scout-public/job-scout
./install.sh       # macOS/Linux
# install.bat      # Windows
```

## Reporting bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) issue template. Include:
- Your OS and Python version
- The exact command you ran
- The full error output

## Suggesting features

Open an issue with the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) template.

## Submitting a PR

1. Fork the repo and create a branch (`git checkout -b feature/my-thing`)
2. Make your changes
3. Test locally (`./start.sh` or `start.bat`)
4. Open a PR against `main` — describe what changed and why

## Code style

- Python: follow PEP 8, keep functions focused
- No new dependencies unless essential — the install footprint matters for ease of use
- If you change the Flask API, update the endpoint table in `job-scout/README.md`

## License

By contributing, you agree your work is released under the [MIT License](LICENSE).
