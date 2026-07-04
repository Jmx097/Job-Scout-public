"""
Plinko Pocket: Job Scout - Backend API
"""

import json
import math
import os
import re
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from flask_cors import CORS


def parse_cv_pdf(path):
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return f"[PDF parse error: {e}]"


def parse_cv_docx(path):
    try:
        import docx

        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return f"[DOCX parse error: {e}]"


def extract_cv_keywords(text):
    tech_skills = [
        "Python",
        "JavaScript",
        "TypeScript",
        "React",
        "Node.js",
        "SQL",
        "AWS",
        "Azure",
        "GCP",
        "Docker",
        "Kubernetes",
        "REST",
        "GraphQL",
        "API",
        "Salesforce",
        "HubSpot",
        "Marketo",
        "Tableau",
        "PowerBI",
        "Excel",
        "Jira",
        "Confluence",
        "Slack",
        "Zapier",
        "Make",
        "n8n",
        "CRM",
        "ERP",
        "SaaS",
        "B2B",
        "Java",
        "Go",
        "Rust",
        "Ruby",
        "PHP",
        "C#",
        ".NET",
        "Machine Learning",
        "AI",
        "Data Science",
        "Analytics",
        "Agile",
        "Scrum",
    ]
    role_keywords = [
        "Solutions Engineer",
        "Sales Engineer",
        "Pre-Sales",
        "Post-Sales",
        "Customer Success",
        "Account Executive",
        "Account Manager",
        "Business Development",
        "Product Manager",
        "Software Engineer",
        "Data Engineer",
        "DevOps",
        "Platform Engineer",
        "Full Stack",
        "Frontend",
        "Backend",
        "Marketing",
        "Operations",
        "Finance",
        "Strategy",
    ]
    text_lower = text.lower()
    found_skills = [s for s in tech_skills if s.lower() in text_lower]
    found_roles = [r for r in role_keywords if r.lower() in text_lower]
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text)
    yoe_match = re.search(r"(\d+)\+?\s*years?", text, re.I)

    suggested_search = ""
    for preferred in ("Sales Engineer", "Solutions Engineer", "Pre-Sales"):
        if preferred in found_roles:
            suggested_search = preferred
            break
    if not suggested_search and found_roles:
        suggested_search = found_roles[0]

    return {
        "skills": found_skills,
        "roles": found_roles,
        "email": emails[0] if emails else None,
        "years_experience": yoe_match.group(1) if yoe_match else None,
        "word_count": len(text.split()),
        "suggested_search_term": suggested_search,
    }


def derive_careers_url(company_url, job_url, company):
    if "linkedin.com/company/" in (company_url or ""):
        slug = company_url.rstrip("/").split("/")[-1]
        return f"https://www.linkedin.com/company/{slug}/jobs/"
    skip = [
        "linkedin",
        "indeed",
        "glassdoor",
        "ziprecruiter",
        "google",
        "lever",
        "greenhouse",
        "workday",
        "workable",
        "bamboohr",
        "ashby",
        "rippling",
    ]
    for url in [company_url, job_url]:
        if not url:
            continue
        try:
            parsed = urlparse(url if url.startswith("http") else f"https://{url}")
            domain = parsed.netloc or parsed.path.split("/")[0]
            if any(s in domain for s in skip):
                continue
            return f"https://{domain}/careers"
        except Exception:
            continue
    safe = re.sub(r"[^a-zA-Z0-9 ]", "", company).strip().replace(" ", "+")
    return f"https://www.google.com/search?q={safe}+careers+jobs"


search_sessions = {}
SESSION_TTL_SECONDS = 1800
STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "for",
    "to",
    "of",
    "in",
    "at",
    "with",
    "role",
    "jobs",
    "job",
    "remote",
}
CORE_TITLE_HINTS = [
    "sales engineer",
    "solutions engineer",
    "solutions consultant",
    "presales",
    "pre-sales",
    "pre sales",
    "presales engineer",
    "pre-sales engineer",
    "sales engineering",
]
ADJACENT_TITLE_HINTS = [
    "solutions architect",
    "technical account manager",
    "customer success engineer",
]
NEGATIVE_TITLE_HINTS = [
    "account executive",
    "account manager",
    "business development",
    "bdr",
    "sdr",
    "recruiter",
    "talent acquisition",
    "customer success manager",
    "project manager",
    "product manager",
    "program manager",
    "marketing manager",
    "software engineer",
    "full stack",
    "frontend engineer",
    "backend engineer",
    "data engineer",
    "devops engineer",
]


def _cleanup_sessions():
    cutoff = time.time() - SESSION_TTL_SECONDS
    stale = [
        sid
        for sid, s in search_sessions.items()
        if s.get("status") in ("done", "error") and s.get("finished_at", 0) < cutoff
    ]
    for sid in stale:
        del search_sessions[sid]


def _is_missing(val):
    if val is None:
        return True
    try:
        if math.isnan(float(val)):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(val, str) and val.strip().lower() in {"", "nan", "none", "null", "nat"}:
        return True
    return False


def _clean_text(val):
    if _is_missing(val):
        return ""
    return str(val).strip()


def _safe_num(val):
    if _is_missing(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _clean_bool(val):
    if isinstance(val, bool):
        return val
    if _is_missing(val):
        return False
    if isinstance(val, (int, float)):
        return bool(val)
    text = str(val).strip().lower()
    return text in {"1", "true", "yes", "y", "remote"}


def _looks_remote(row):
    if _clean_bool(row.get("is_remote")):
        return True
    title = _clean_text(row.get("title")).lower()
    location_bits = [
        _clean_text(row.get("city")).lower(),
        _clean_text(row.get("state")).lower(),
        _clean_text(row.get("country")).lower(),
    ]
    combined_location = " ".join(bit for bit in location_bits if bit)
    return "remote" in title or "remote" in combined_location


def _tokenize(text):
    tokens = re.findall(r"[a-z0-9+#.]+", (text or "").lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def _find_matching_hint(title, hints):
    return next((hint for hint in hints if hint in title), "")


def _score_job(row, params):
    title = _clean_text(row.get("title")).lower()
    description = _clean_text(row.get("description")).lower()
    company = _clean_text(row.get("company")).lower()
    industry = _clean_text(row.get("company_industry")).lower()
    combined = " ".join(part for part in [title, description, company, industry] if part)

    search_term = _clean_text(params.get("search_term")).lower()
    search_tokens = _tokenize(search_term)
    exclude_keywords = [kw.lower() for kw in params.get("exclude_keywords", []) if kw]
    is_remote_requested = bool(params.get("is_remote"))
    requested_job_type = _clean_text(params.get("job_type")).lower()

    score = 0
    reasons = []
    strong_title_alignment = False

    if search_term:
        if search_term in title:
            score += 52
            reasons.append("exact title phrase")
            strong_title_alignment = True
        elif all(token in title for token in search_tokens) and search_tokens:
            score += 34
            reasons.append("all title keywords")
            strong_title_alignment = True

        title_hits = sum(1 for token in search_tokens if token in title)
        if title_hits:
            score += min(24, title_hits * 8)
            reasons.append(f"{title_hits} title keyword match")
            if title_hits >= max(2, min(len(search_tokens), 2)):
                strong_title_alignment = True

        desc_hits = sum(1 for token in search_tokens if token in combined and token not in title)
        if desc_hits:
            score += min(8, desc_hits * 2)
            reasons.append(f"{desc_hits} broader keyword match")

    core_hint = _find_matching_hint(title, CORE_TITLE_HINTS)
    adjacent_hint = _find_matching_hint(title, ADJACENT_TITLE_HINTS)
    negative_hint = _find_matching_hint(title, NEGATIVE_TITLE_HINTS)

    if core_hint:
        score += 38
        reasons.append("core title family")
        strong_title_alignment = True
    elif adjacent_hint:
        score += 10
        reasons.append("adjacent title family")

    if core_hint and search_tokens and any(token in title for token in search_tokens):
        score += 10
        reasons.append("core title overlap")

    if search_tokens and not any(token in title for token in search_tokens[:2]):
        score -= 16

    if negative_hint:
        score -= 45
        reasons.append("off-target title family")

    if search_term and not strong_title_alignment:
        score -= 20
        reasons.append("weak title alignment")

    if is_remote_requested:
        if _looks_remote(row):
            score += 8
            reasons.append("remote match")
        else:
            score -= 8

    job_type = _clean_text(row.get("job_type")).lower()
    if requested_job_type:
        if requested_job_type and requested_job_type == job_type:
            score += 6
            reasons.append("job type match")
        elif job_type:
            score -= 6

    if _safe_num(row.get("min_amount")) is not None or _safe_num(row.get("max_amount")) is not None:
        score += 3
        reasons.append("salary data present")

    if exclude_keywords and any(keyword in title for keyword in exclude_keywords):
        score -= 100
        reasons.append("excluded title keyword")

    if search_term and not strong_title_alignment:
        score = min(score, 44)

    score = max(0, min(100, score))
    if score >= 70:
        label = "High"
    elif score >= 45:
        label = "Medium"
    else:
        label = "Low"

    deduped_reasons = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)

    return score, label, deduped_reasons[:3]


UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static")
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000"])
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": "1.1.0"})


@app.route("/api/upload-cv", methods=["POST"])
def upload_cv():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".doc", ".txt"}:
        return jsonify({"error": "Unsupported file type. Use PDF, DOCX, or TXT."}), 400
    save_path = UPLOAD_FOLDER / f"cv{ext}"
    f.save(str(save_path))
    if ext == ".pdf":
        text = parse_cv_pdf(str(save_path))
    elif ext in {".docx", ".doc"}:
        text = parse_cv_docx(str(save_path))
    else:
        text = save_path.read_text(errors="ignore")
    keywords = extract_cv_keywords(text)
    return jsonify(
        {
            "success": True,
            "filename": f.filename,
            "keywords": keywords,
            "text_preview": text[:500].strip(),
        }
    )


def _run_search(session_id, params):
    sess = search_sessions[session_id]
    sess["status"] = "running"
    sess["events"] = []

    def emit(event_type, data):
        sess["events"].append({"type": event_type, "data": data})

    try:
        from jobspy import scrape_jobs

        sites = params.get("sites", ["indeed", "linkedin", "zip_recruiter", "google"])
        search_term = params.get("search_term", "")
        location = params.get("location", "")
        is_remote = params.get("is_remote", False)
        job_type = params.get("job_type") or None
        hours_old = int(params.get("hours_old", 72))
        results_per = int(params.get("results_per_site", 15))
        country = params.get("country_indeed", "USA")
        google_term = params.get("google_search_term") or f"{search_term} jobs {location}"
        min_fit_score = int(params.get("min_fit_score", 50))

        emit("progress", {"message": f"Searching {len(sites)} sources...", "pct": 5})

        jobs_df = scrape_jobs(
            site_name=sites,
            search_term=search_term,
            google_search_term=google_term,
            location=location,
            is_remote=is_remote,
            job_type=job_type,
            hours_old=hours_old,
            results_wanted=results_per,
            country_indeed=country,
            linkedin_fetch_description=False,
            verbose=0,
        )

        emit("progress", {"message": f"Found {len(jobs_df)} listings, scoring fit...", "pct": 80})

        results = []
        for _, row in jobs_df.iterrows():
            company = _clean_text(row.get("company"))
            title = _clean_text(row.get("title"))
            job_url = _clean_text(row.get("job_url"))
            company_url = _clean_text(row.get("company_url"))
            city = _clean_text(row.get("city"))
            state = _clean_text(row.get("state"))
            country_val = _clean_text(row.get("country"))
            remote = _looks_remote(row)
            jtype = _clean_text(row.get("job_type"))
            site = _clean_text(row.get("site"))
            date_posted = _clean_text(row.get("date_posted"))
            logo = _clean_text(row.get("company_logo"))
            industry = _clean_text(row.get("company_industry"))
            description = _clean_text(row.get("description"))[:300]

            interval = _clean_text(row.get("interval"))
            min_amt = _safe_num(row.get("min_amount"))
            max_amt = _safe_num(row.get("max_amount"))
            currency = _clean_text(row.get("currency")) or "USD"
            salary_str = ""
            if min_amt is not None and max_amt is not None:
                salary_str = f"{currency} {int(min_amt):,} - {int(max_amt):,}"
                if interval:
                    salary_str += f" / {interval}"
            elif min_amt is not None:
                salary_str = f"{currency} {int(min_amt):,}+"
                if interval:
                    salary_str += f" / {interval}"
            elif max_amt is not None:
                salary_str = f"{currency} up to {int(max_amt):,}"
                if interval:
                    salary_str += f" / {interval}"

            location_str = ", ".join(part for part in [city, state, country_val] if part)
            careers_url = derive_careers_url(company_url, job_url, company)
            fit_score, fit_label, fit_reasons = _score_job(row, params)

            if fit_score < min_fit_score:
                continue

            results.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "company": company,
                    "company_url": company_url,
                    "careers_url": careers_url,
                    "job_url": job_url,
                    "location": location_str,
                    "is_remote": remote,
                    "job_type": jtype,
                    "site": site,
                    "date_posted": date_posted,
                    "salary": salary_str,
                    "logo": logo,
                    "industry": industry,
                    "description": description,
                    "fit_score": fit_score,
                    "fit_label": fit_label,
                    "fit_reasons": fit_reasons,
                }
            )

        results.sort(key=lambda item: (item["fit_score"], item["salary"] != "", item["date_posted"]), reverse=True)

        sess["results"] = results
        sess["status"] = "done"
        sess["finished_at"] = time.time()
        emit("done", {"count": len(results)})

    except ImportError:
        sess["status"] = "error"
        sess["finished_at"] = time.time()
        emit("error", {"message": "jobspy not installed. Run: pip install python-jobspy"})
    except Exception as e:
        sess["status"] = "error"
        sess["finished_at"] = time.time()
        emit("error", {"message": str(e)})


@app.route("/api/search", methods=["POST"])
def start_search():
    _cleanup_sessions()
    params = request.get_json(force=True)
    if not params.get("search_term"):
        return jsonify({"error": "search_term is required"}), 400
    session_id = str(uuid.uuid4())
    search_sessions[session_id] = {
        "status": "queued",
        "events": [],
        "results": [],
        "params": params,
    }
    t = threading.Thread(target=_run_search, args=(session_id, params), daemon=True)
    t.start()
    return jsonify({"session_id": session_id})


@app.route("/api/search/<session_id>/stream")
def stream_search(session_id):
    if session_id not in search_sessions:
        return jsonify({"error": "Session not found"}), 404

    def generate():
        seen = 0
        while True:
            sess = search_sessions.get(session_id, {})
            events = sess.get("events", [])
            while seen < len(events):
                yield f"data: {json.dumps(events[seen])}\n\n"
                seen += 1
            if sess.get("status") in ("done", "error"):
                break
            time.sleep(0.4)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "http://localhost:5000",
        },
    )


@app.route("/api/search/<session_id>/results")
def get_results(session_id):
    sess = search_sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(
        {
            "status": sess["status"],
            "results": sess["results"],
            "count": len(sess["results"]),
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Plinko Pocket: Job Scout running at http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


