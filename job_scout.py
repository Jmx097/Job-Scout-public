#!/usr/bin/env python3
"""
job_scout.py — CLI job search tool powered by JobSpy.

Searches LinkedIn, Indeed, and ZipRecruiter simultaneously, filters and scores
results, then outputs a CSV and a Markdown shortlist with direct company
career-page links (not ephemeral job-board URLs).

Outputs
-------
  jobs_raw.csv        — everything scraped (useful for debugging / tuning)
  jobs_filtered.csv   — matches after all filters, ranked by signal score
  shortlist.md        — top 25 with company careers-page links

Usage
-----
  pip install -U python-jobspy pandas
  python job_scout.py

Repo: https://github.com/Jmx097/Job-Scout-public
"""

import csv
import re
import sys
from datetime import datetime
from urllib.parse import urlparse, quote_plus

import pandas as pd
from jobspy import scrape_jobs

# =============================================================================
# ██████  CONFIG — edit this section to match your search
# =============================================================================

# One or more search terms. Use quoted phrases and -exclusions to narrow.
# Examples:
#   '"solutions engineer" AI remote'
#   '"product manager" fintech -senior'
#   '"data analyst" healthcare remote'
SEARCH_TERMS = [
    '"solutions engineer" AI remote -senior -staff -principal',
    '"sales engineer" AI remote -senior -staff -principal',
    '"solutions architect" AI remote -senior -staff -principal',
    '"customer success manager" AI remote -senior -director',
    '"technical account manager" AI remote -senior',
    '"AI product manager" remote -senior -principal -director',
    '"forward deployed engineer" remote -senior',
]

# Job boards to search. Options: "indeed", "linkedin", "zip_recruiter", "glassdoor"
SITES = ["indeed", "zip_recruiter", "linkedin"]

# Results to fetch per search term per site (higher = slower + more rate-limiting)
RESULTS_PER_TERM_PER_SITE = 25

# Only include jobs posted within this many hours (LinkedIn/Indeed honor this best)
HOURS_OLD = 96

# Minimum annual salary. Jobs with no salary listed are kept but scored lower.
# Set to 0 to disable the salary filter entirely.
MIN_SALARY = 120_000

# Country for Indeed searches ("USA", "Canada", "UK", "Australia", etc.)
COUNTRY = "USA"

# Title exclusion filter — jobs whose titles match this regex are dropped.
# Adjust or replace the pattern to match your target seniority level.
EXCLUDE_TITLE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|director|vp|vice president|head of|"
    r"chief|intern|internship|manager,? (?:engineering|software)|junior|jr\.?)\b",
    re.I,
)

# Title inclusion filter — only jobs whose titles match this are kept.
# Replace with your target roles.
INCLUDE_TITLE = re.compile(
    r"(solutions? (engineer|architect|consultant)|sales engineer|"
    r"pre-?sales|customer success|technical account manager|"
    r"product manager|forward deployed|implementation (engineer|manager|specialist)|"
    r"solutions specialist)",
    re.I,
)

# Keywords that indicate AI-relevance (used for scoring, not filtering).
# Matches in the title score higher than matches in the description.
AI_KEYWORDS = re.compile(
    r"\b(AI|artificial intelligence|machine learning|ML|LLM|GenAI|"
    r"generative|NLP|deep learning|copilot|agentic|foundation model)\b",
    re.I,
)

# Proxies to use (recommended for LinkedIn to avoid rate limits).
# Format: ["user:pass@host:port", ...]  — leave empty to skip.
PROXIES = []

# =============================================================================
# END CONFIG
# =============================================================================


US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}


# ── Scraping ──────────────────────────────────────────────────────────────────

def scrape_all() -> pd.DataFrame:
    frames = []
    for term in SEARCH_TERMS:
        for site in SITES:
            kwargs = dict(
                site_name=site,
                search_term=term,
                location="United States",
                results_wanted=RESULTS_PER_TERM_PER_SITE,
                country_indeed=COUNTRY,
                description_format="markdown",
                enforce_annual_salary=True,
                verbose=0,
            )
            if PROXIES:
                kwargs["proxies"] = PROXIES
            # Indeed/LinkedIn: hours_old can't combine with is_remote —
            # use hours_old and filter remote post-hoc via search term or flag.
            if site in ("indeed", "linkedin"):
                kwargs["hours_old"] = HOURS_OLD
                if site == "linkedin":
                    kwargs["linkedin_fetch_description"] = True
            else:
                kwargs["is_remote"] = True
                kwargs["hours_old"] = HOURS_OLD
            try:
                df = scrape_jobs(**kwargs)
                if df is not None and len(df):
                    df["search_term_used"] = term
                    frames.append(df)
                    print(f"  {site:>13} | {len(df):>3} jobs | {term}")
            except Exception as e:
                print(f"  {site:>13} | ERROR: {e}", file=sys.stderr)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return out.drop_duplicates(subset=["title", "company"], keep="first")


# ── Filters ───────────────────────────────────────────────────────────────────

def is_us(row) -> bool:
    loc = str(row.get("location") or "")
    if "United States" in loc or "USA" in loc:
        return True
    parts = [p.strip() for p in loc.split(",")]
    return any(p.upper() in US_STATES for p in parts)


def remote_ok(row) -> bool:
    if row.get("is_remote") is True:
        return True
    text = f"{row.get('title', '')} {row.get('location', '')}"
    return bool(re.search(r"\bremote\b", str(text), re.I))


def salary_ok(row) -> bool:
    """Keep if max comp >= MIN_SALARY, or if no salary is listed (unlisted = keep)."""
    if MIN_SALARY == 0:
        return True
    mx = row.get("max_amount")
    mn = row.get("min_amount")
    interval = str(row.get("interval") or "")
    for v in (mx, mn):
        try:
            v = float(v)
            if interval == "hourly":
                v *= 2080
            if v >= MIN_SALARY:
                return True
        except (TypeError, ValueError):
            pass
    # No salary listed — keep but it scores lower
    if pd.isna(mx) and pd.isna(mn):
        return True
    return False


def level_ok(row) -> bool:
    if EXCLUDE_TITLE.search(str(row.get("title") or "")):
        return False
    lvl = str(row.get("job_level") or "").lower()
    return lvl not in ("director", "executive")


def role_ok(row) -> bool:
    return bool(INCLUDE_TITLE.search(str(row.get("title") or "")))


# ── Career-page derivation ────────────────────────────────────────────────────

ATS_PATTERNS = [
    (r"boards\.greenhouse\.io/([^/]+)", "https://boards.greenhouse.io/{}"),
    (r"job-boards\.greenhouse\.io/([^/]+)", "https://job-boards.greenhouse.io/{}"),
    (r"jobs\.lever\.co/([^/]+)", "https://jobs.lever.co/{}"),
    (r"jobs\.ashbyhq\.com/([^/]+)", "https://jobs.ashbyhq.com/{}"),
    (r"jobs\.smartrecruiters\.com/([^/]+)", "https://jobs.smartrecruiters.com/{}"),
    (r"([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com/([^/?]+)",
     "https://{}.wd1.myworkdayjobs.com/{}"),
    (r"apply\.workable\.com/([^/]+)", "https://apply.workable.com/{}"),
    (r"([a-z0-9-]+)\.breezy\.hr", "https://{}.breezy.hr"),
    (r"jobs\.jobvite\.com/([^/]+)", "https://jobs.jobvite.com/{}"),
]


def career_page(row) -> str:
    """Return the company's ATS/careers page URL, or a Google fallback."""
    direct = str(row.get("job_url_direct") or "")
    for pat, tmpl in ATS_PATTERNS:
        m = re.search(pat, direct)
        if m:
            return tmpl.format(*m.groups())
    if direct.startswith("http"):
        host = urlparse(direct).netloc
        if not any(b in host for b in ("indeed", "linkedin", "ziprecruiter", "glassdoor")):
            return f"https://{host}"
    company = str(row.get("company") or "")
    return f"https://www.google.com/search?q={quote_plus(company + ' careers')}"


# ── Scoring ───────────────────────────────────────────────────────────────────

def ai_score(row) -> int:
    """Count AI-keyword hits (title weighted higher than description)."""
    s = 0
    if AI_KEYWORDS.search(str(row.get("title") or "")):
        s += 3
    if AI_KEYWORDS.search(str(row.get("company") or "")):
        s += 2
    s += min(len(AI_KEYWORDS.findall(str(row.get("description") or ""))), 5)
    return s


def signal_score(row) -> float:
    """Higher = stronger signal & easier to apply."""
    s = float(ai_score(row))
    if pd.notna(row.get("max_amount")) or pd.notna(row.get("min_amount")):
        s += 2                          # transparent comp = serious posting
    if not career_page(row).startswith("https://www.google.com"):
        s += 3                          # real ATS page found = easy apply
    try:
        days = (datetime.now().date() - pd.to_datetime(row.get("date_posted")).date()).days
        s += max(0, 3 - days)           # fresher is better
    except Exception:
        pass
    if row.get("is_remote") is True:
        s += 1
    return s


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Scraping jobs...")
    raw = scrape_all()
    print(f"\nTotal scraped (deduped): {len(raw)}")
    if raw.empty:
        sys.exit("No jobs scraped — likely rate-limited. Wait and retry, or add proxies.")

    raw.to_csv("jobs_raw.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
    print(f"  → jobs_raw.csv saved ({len(raw)} rows)")

    # Apply filters
    df = raw[raw.apply(is_us, axis=1)]
    df = df[df.apply(remote_ok, axis=1)]
    df = df[df.apply(level_ok, axis=1)]
    df = df[df.apply(role_ok, axis=1)]
    df = df[df.apply(salary_ok, axis=1)]
    print(f"After filters (US · remote · level · role · salary): {len(df)}")

    if df.empty:
        sys.exit("No jobs passed the filters — try relaxing HOURS_OLD, MIN_SALARY, or INCLUDE_TITLE.")

    # Score and sort
    df = df.copy()
    df["career_page"]   = df.apply(career_page, axis=1)
    df["ai_score"]      = df.apply(ai_score, axis=1)
    df["signal_score"]  = df.apply(signal_score, axis=1)
    df = df.sort_values("signal_score", ascending=False)

    keep = ["title", "company", "career_page", "signal_score", "ai_score",
            "min_amount", "max_amount", "date_posted", "location", "site",
            "job_url", "job_url_direct"]
    df[[c for c in keep if c in df.columns]].to_csv(
        "jobs_filtered.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
    print(f"  → jobs_filtered.csv saved ({len(df)} rows)")

    # Markdown shortlist
    lines = [
        f"# Job Shortlist — {datetime.now():%Y-%m-%d}",
        "",
        "Filtered · ranked by signal score · links go to **company career pages**.",
        "",
    ]
    for _, r in df.head(25).iterrows():
        sal = ""
        if pd.notna(r.get("min_amount")) and pd.notna(r.get("max_amount")):
            sal = f" — ${r['min_amount']:,.0f}–${r['max_amount']:,.0f}"
        elif pd.notna(r.get("max_amount")):
            sal = f" — up to ${r['max_amount']:,.0f}"
        lines.append(
            f"- **{r['title']}** @ {r['company']}{sal}  \n"
            f"  Career page: <{r['career_page']}>  \n"
            f"  Posted: {r.get('date_posted')} · Signal: {r['signal_score']:.0f} "
            f"· AI: {r['ai_score']} · via {r.get('site')}"
        )
    with open("shortlist.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  → shortlist.md saved (top {min(25, len(df))} results)")


if __name__ == "__main__":
    main()
