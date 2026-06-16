"""
Plinko Pocket: Job Scout - Backend API
"""

import json
import math
import os
import re
import time
import threading
import uuid
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS

# ── CV parsing ───────────────────────────────────────────────────────────────

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
        "Python","JavaScript","TypeScript","React","Node.js","SQL","AWS","Azure","GCP",
        "Docker","Kubernetes","REST","GraphQL","API","Salesforce","HubSpot","Marketo",
        "Tableau","PowerBI","Excel","Jira","Confluence","Slack","Zapier","Make","n8n",
        "CRM","ERP","SaaS","B2B","Java","Go","Rust","Ruby","PHP","C#",".NET",
        "Machine Learning","AI","Data Science","Analytics","Agile","Scrum",
    ]
    role_keywords = [
        "Solutions Engineer","Sales Engineer","Pre-Sales","Post-Sales","Customer Success",
        "Account Executive","Account Manager","Business Development","Product Manager",
        "Software Engineer","Data Engineer","DevOps","Platform Engineer","Full Stack",
        "Frontend","Backend","Marketing","Operations","Finance","Strategy",
    ]
    text_lower = text.lower()
    found_skills = [s for s in tech_skills if s.lower() in text_lower]
    found_roles  = [r for r in role_keywords if r.lower() in text_lower]
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', text)
    yoe_match = re.search(r'(\d+)\+?\s*years?', text, re.I)
    return {
        "skills": found_skills,
        "roles": found_roles,
        "email": emails[0] if emails else None,
        "years_experience": yoe_match.group(1) if yoe_match else None,
        "word_count": len(text.split()),
        "suggested_search_term": found_roles[0] if found_roles else "",
    }

# ── Careers URL derivation ───────────────────────────────────────────────────

def derive_careers_url(company_url, job_url, company):
    if "linkedin.com/company/" in (company_url or ""):
        slug = company_url.rstrip("/").split("/")[-1]
        return f"https://www.linkedin.com/company/{slug}/jobs/"
    skip = ["linkedin","indeed","glassdoor","ziprecruiter","google","lever",
            "greenhouse","workday","workable","bamboohr","ashby","rippling"]
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
    safe = re.sub(r'[^a-zA-Z0-9 ]', '', company).strip().replace(" ", "+")
    return f"https://www.google.com/search?q={safe}+careers+jobs"

# ── Session store ────────────────────────────────────────────────────────────

search_sessions = {}

# ── Flask app ────────────────────────────────────────────────────────────────

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})

# ── CV upload ────────────────────────────────────────────────────────────────

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
    return jsonify({
        "success": True,
        "filename": f.filename,
        "keywords": keywords,
        "text_preview": text[:500].strip(),
    })

# ── Job search ───────────────────────────────────────────────────────────────

def _safe_num(val):
    if val is None:
        return None
    try:
        if math.isnan(float(val)):
            return None
    except (TypeError, ValueError):
        return None
    return val

def _run_search(session_id, params):
    sess = search_sessions[session_id]
    sess["status"] = "running"
    sess["events"] = []

    def emit(event_type, data):
        sess["events"].append({"type": event_type, "data": data})

    try:
        from jobspy import scrape_jobs

        sites       = params.get("sites", ["indeed", "linkedin", "zip_recruiter", "google"])
        search_term = params.get("search_term", "")
        location    = params.get("location", "")
        is_remote   = params.get("is_remote", False)
        job_type    = params.get("job_type") or None
        hours_old   = int(params.get("hours_old", 72))
        results_per = int(params.get("results_per_site", 15))
        country     = params.get("country_indeed", "USA")
        google_term = params.get("google_search_term") or f"{search_term} jobs {location}"

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

        emit("progress", {"message": f"Found {len(jobs_df)} listings, building results...", "pct": 80})

        results = []
        for _, row in jobs_df.iterrows():
            company     = str(row.get("company") or "")
            title       = str(row.get("title") or "")
            job_url     = str(row.get("job_url") or "")
            company_url = str(row.get("company_url") or "")
            city        = str(row.get("city") or "")
            state       = str(row.get("state") or "")
            country_val = str(row.get("country") or "")
            remote      = bool(row.get("is_remote"))
            jtype       = str(row.get("job_type") or "")
            site        = str(row.get("site") or "")
            date_posted = str(row.get("date_posted") or "")
            logo        = str(row.get("company_logo") or "")
            industry    = str(row.get("company_industry") or "")
            description = str(row.get("description") or "")[:300]

            interval = str(row.get("interval") or "")
            min_amt  = _safe_num(row.get("min_amount"))
            max_amt  = _safe_num(row.get("max_amount"))
            currency = str(row.get("currency") or "USD")
            salary_str = ""
            if min_amt is not None and max_amt is not None:
                salary_str = f"{currency} {int(min_amt):,} - {int(max_amt):,} / {interval}"
            elif min_amt is not None:
                salary_str = f"{currency} {int(min_amt):,}+ / {interval}"

            location_str = ", ".join(filter(None, [city, state, country_val]))
            careers_url  = derive_careers_url(company_url, job_url, company)

            results.append({
                "id":          str(uuid.uuid4()),
                "title":       title,
                "company":     company,
                "company_url": company_url,
                "careers_url": careers_url,
                "job_url":     job_url,
                "location":    location_str,
                "is_remote":   remote,
                "job_type":    jtype,
                "site":        site,
                "date_posted": date_posted,
                "salary":      salary_str,
                "logo":        logo,
                "industry":    industry,
                "description": description,
            })

        sess["results"] = results
        sess["status"]  = "done"
        emit("done", {"count": len(results)})

    except ImportError:
        sess["status"] = "error"
        emit("error", {"message": "jobspy not installed. Run: pip install python-jobspy"})
    except Exception as e:
        sess["status"] = "error"
        emit("error", {"message": str(e)})

@app.route("/api/search", methods=["POST"])
def start_search():
    params = request.get_json(force=True)
    if not params.get("search_term"):
        return jsonify({"error": "search_term is required"}), 400
    session_id = str(uuid.uuid4())
    search_sessions[session_id] = {
        "status":  "queued",
        "events":  [],
        "results": [],
        "params":  params,
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
            sess   = search_sessions.get(session_id, {})
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
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )

@app.route("/api/search/<session_id>/results")
def get_results(session_id):
    sess = search_sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "status":  sess["status"],
        "results": sess["results"],
        "count":   len(sess["results"]),
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Plinko Pocket: Job Scout running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
