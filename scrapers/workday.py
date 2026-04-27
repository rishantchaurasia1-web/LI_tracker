import json
from common import HEADERS

# Each entry: (tenant_subdomain, site_id, friendly_company_name)
# URL pattern: https://{tenant}.{wd_dc}.myworkdayjobs.com/{site_id}
# These need verification — Workday URLs change.
WORKDAY_COMPANIES = [
    # Many big PE/RE shops. Format below assumes wd1; some are wd3, wd5 etc.
    # If a company doesn't return data, check the URL in your browser.
    ("blackstone", "wd1", "Blackstone-Careers", "Blackstone"),
    ("kkr", "wd1", "KKR_Careers", "KKR"),
    ("apollo", "wd1", "apollo_careers", "Apollo"),
    ("ares", "wd1", "Ares_External_Careers", "Ares"),
    ("brookfield", "wd5", "Brookfield_Careers", "Brookfield"),
    ("carlyle", "wd1", "Carlyle_Careers", "Carlyle"),
    ("oaktree", "wd1", "OaktreeCareers", "Oaktree"),
    ("jll", "wd1", "JLLCareers", "JLL"),
    ("cbre", "wd1", "CBRE", "CBRE"),
    ("cushwake", "wd1", "CushmanWakefield", "Cushman & Wakefield"),
    ("hines", "wd1", "Hines", "Hines"),
    ("pgim", "wd1", "PGIM", "PGIM"),
]

WORKDAY_HEADERS = {
    **HEADERS,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

KEYWORDS = [
    "real estate", "acquisitions", "underwriting", "investment",
    "financial model", "valuation", "asset management",
    "portfolio analyst", "private equity",
]


def fetch_all(client):
    all_jobs = []
    for tenant, dc, site_id, friendly in WORKDAY_COMPANIES:
        for kw in KEYWORDS:
            base = f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site_id}/jobs"
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": kw,
            }
            try:
                r = client.post(base, headers=WORKDAY_HEADERS, json=payload)
                if r.status_code != 200:
                    continue
                data = r.json()
                for job in data.get("jobPostings", []):
                    ext_url = job.get("externalPath", "")
                    jid = ext_url.split("/")[-1] if ext_url else ""
                    if not jid:
                        continue
                    title = job.get("title", "")
                    loc = job.get("locationsText", "?")
                    posted = job.get("postedOn", "recent")
                    all_jobs.append({
                        "id": f"wd-{tenant}-{jid}",
                        "title": title,
                        "company": friendly,
                        "location": loc,
                        "posted": posted,
                        "url": f"https://{tenant}.{dc}.myworkdayjobs.com/{site_id}{ext_url}",
                        "jd_url": f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site_id}/job{ext_url}",
                        "source": "Workday",
                    })
            except Exception as e:
                print(f"    [wd:{tenant}:{kw}] error: {e}", flush=True)
    return all_jobs
