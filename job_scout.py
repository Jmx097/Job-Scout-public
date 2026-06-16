#!/usr/bin/env python3
"""
job_scout.py — JobSpy-based job sourcing script.

Targets: US-based, 100% remote, $120k+, non-senior, AI-related roles in
customer success / solutions engineering / presales / AI product.

Outputs:
  jobs_raw.csv        — everything scraped (for debugging/tuning)
  jobs_filtered.csv   — matches after all filters, scored by signal
  shortlist.md        — top matches with company CAREER PAGE links (not job-board links)

Usage:
  pip install -U python-jobspy
  python job_scout.py
"""

import csv
import re
import sys
from datetime import datetime
from urllib.parse import urlparse, quote_plus

import pandas as pd
from jobspy import scrape_jobs

# ----------------------------- CONFIG ---------------------------------------

SEARCH_TERMS = [
    '"solutions engineer" AI remote -senior -staff -principal',
    '"sales engineer" AI remote -senior -staff -principal',
    '"solutions architect" AI remote -senior -staff -principal',
    '"customer success manager" AI remote -senior -director',
    '"technical account manager" AI remote -senior',
    '"AI product manager" remote -senior -principal -director',
    '"forward deployed engineer" remote -senior',
]

SITES = ["indeed", "zip_recruiter", "linkedin"]
RESULTS_PER_TERM_PER_SITE = 25
HOURS_OLD = 96          # recently posted only (LinkedIn/Indeed honor this)
MIN_SALARY = 120_000
COUNTRY = "USA"

# Title must NOT contain (seniority / wrong-level filter)
EXCLUDE_TITLE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|director|vp|vice president|head of|"
    r"chief|intern|internship|manager,? (?:engineering|software)|junior|jr\.?)\b",
    re.I,
)

# Title must contain at least one (role-relevance filter)
INCLUDE_TITLE = re.compile(
    r"(solutions? (engineer|architect|consultant)|sales engineer|"
    r"pre-?sales|customer success|technical account manager|"
    r"product manager|forward deployed|implementation (engineer|manager|specialist)|"
    r"solutions specialist)",
    re.I,
)

# AI-relatedness keywords (title/description/company) — used for scoring
AI_KEYWORDS = re.compile(
    r"\b(AI|artificial intelligence|machine learning|ML|LLM|GenAI|"
    r"generative|NLP|deep learning|copilot|agentic|foundation model)\b",
    re.I,
)

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}

# ----------------------------- SCRAPE ---------------------------------------

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
            # Indeed/LinkedIn: hours_old can't combine with is_remote ->
            # use hours_old and filter remote post-hoc (term contains "remote").
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

# ----------------------------- FILTERS --------------------------------------

def is_us(row) -> bool:
    loc = str(row.get("location") or "")
    if "United States" in loc or "USA" in loc:
        return True
    parts = [p.strip() for p in loc.split(",")]
    return any(p.upper() in US_STATES for p in parts)


def remote_ok(row) -> bool:
    if row.get("is_remote") is True:
        return True
    text = f"{row.get('title','')} {row.get('location','')}"
    return bool(re.search(r"\bremote\b", str(text), re.I))


def salary_ok(row) -> bool:
    """Keep if max comp >= MIN_SALARY, or salary unlisted but desc mentions 120k+."""
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
    if pd.isna(mx) and pd.isna(mn):
        desc = str(row.get("description") or "")
        m = re.findall(r"\$\s?(\d{3})[,.]?\d{3}", desc)
        return any(int(x) >= 120 for x in m)
    return False


def level_ok(row) -> bool:
    if EXCLUDE_TITLE.search(str(row.get("title") or "")):
        return False
    lvl = str(row.get("job_level") or "").lower()
    return lvl not in ("director", "executive")


def role_ok(row) -> bool:
    return bool(INCLUDE_TITLE.search(str(row.get("title") or "")))

# ----------------------------- SCORING --------------------------------------

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
    """Derive a company career-page URL from the direct apply URL or fall back
    to a Google 'company careers' search link."""
    direct = str(row.get("job_url_direct") or "")
    for pat, tmpl in ATS_PATTERNS:
        m = re.search(pat, direct)
        if m:
            return tmpl.format(*m.groups())
    if direct.startswith("http"):
        host = urlparse(direct).netloc
        # career subdomain on company site, e.g. careers.company.com
        if not any(b in host for b in ("indeed", "linkedin", "ziprecruiter", "glassdoor")):
            return f"https://{host}"
    company = str(row.get("company") or "")
    return f"https://www.google.com/search?q={quote_plus(company + ' careers')}"


def ai_score(row) -> int:
    s = 0
    title = str(row.get("title") or "")
    company = str(row.get("company") or "")
    desc = str(row.get("description") or "")
    if AI_KEYWORDS.search(title):
        s += 3
    if AI_KEYWORDS.search(company):
        s += 2
    s += min(len(AI_KEYWORDS.findall(desc)), 5)
    return s


def signal_score(row) -> float:
    """Higher = stronger signal & easier apply."""
    s = float(ai_score(row))
    if pd.notna(row.get("max_amount")) or pd.notna(row.get("min_amount")):
        s += 2                      # transparent comp = serious posting
    if not career_page(row).startswith("https://www.google.com"):
        s += 3                      # real ATS/career page found = easy apply
    dp = row.get("date_posted")
    try:
        days = (datetime.now().date() - pd.to_datetime(dp).date()).days
        s += max(0, 3 - days)       # fresher = better
    except Exception:
        pass
    if row.get("is_remote") is True:
        s += 1
    return s

# ----------------------------- MAIN -----------------------------------------

def main():
    print("Scraping...")
    raw = scrape_all()
    print(f"\nTotal scraped (deduped): {len(raw)}")
    if raw.empty:
        sys.exit("No jobs scraped — likely rate-limited. Wait and retry, or add proxies.")

    raw.to_csv("jobs_raw.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)

    df = raw[raw.apply(is_us, axis=1)]
    df = df[df.apply(remote_ok, axis=1)]
    df = df[df.apply(level_ok, axis=1)]
    df = df[df.apply(role_ok, axis=1)]
    df = df[df.apply(salary_ok, axis=1)]
    print(f"After US/remote/level/role/salary filters: {len(df)}")

    if df.empty:
        sys.exit("No jobs passed the filters. Loosen HOURS_OLD or MIN_SALARY.")

    df = df.copy()
    df["career_page"] = df.apply(career_page, axis=1)
    df["ai_score"] = df.apply(ai_score, axis=1)
    df["signal_score"] = df.apply(signal_score, axis=1)
    df = df.sort_values("signal_score", ascending=False)

    keep = ["title", "company", "career_page", "signal_score", "ai_score",
            "min_amount", "max_amount", "date_posted", "location", "site",
            "job_url", "job_url_direct"]
    df[[c for c in keep if c in df.columns]].to_csv(
        "jobs_filtered.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)

    # Markdown shortlist
    lines = [
        f"# Job Shortlist — {datetime.now():%Y-%m-%d}",
        "",
        "US-based · 100% remote · $120k+ · non-senior · AI-weighted. "
        "Links go to **company career pages**, sorted by signal score.",
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

    print(f"\nWrote jobs_raw.csv ({len(raw)}), jobs_filtered.csv ({len(df)}), shortlist.md")


if __name__ == "__main__":
    main()
