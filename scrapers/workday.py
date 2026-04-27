from common import HEADERS

# Each entry: (tenant, datacenter, site_id, friendly_name)
# Only include companies you've VERIFIED exist by visiting:
#   https://{tenant}.{datacenter}.myworkdayjobs.com/{site_id}
# If the page loads with jobs, the entry is valid.
#
# Note: Each company can have multiple "site_ids" — public Careers boards
# often differ from Campus boards. We include both where useful.
WORKDAY_COMPANIES = [
    # Verified
    ("blackstone", "wd1", "Blackstone_Careers",        "Blackstone"),
    ("blackstone", "wd1", "Blackstone_Campus_Careers", "Blackstone (Campus)"),
    # Likely-valid (will be probed; failures are silent)
    ("kkr",        "wd1", "KKR_Careers",               "KKR"),
    ("apollo",     "wd1", "apollo_careers",            "Apollo"),
    ("ares",       "wd1", "Ares_External_Careers",     "Ares"),
    ("brookfield", "wd5", "Brookfield_Careers",        "Brookfield"),
    ("carlyle",    "wd1", "Carlyle_Careers",           "Carlyle"),
    ("oaktree",    "wd1", "OaktreeCareers",            "Oaktree"),
    ("jll",        "wd1", "JLLCareers",                "JLL"),
    ("cbre",       "wd1", "CBRE",                      "CBRE"),
    ("pgim",       "wd1", "PGIM",                      "PGIM"),
    ("nuveen",     "wd1", "nuveen",                    "Nuveen"),
    ("mfs",        "wd1", "MFS",                       "MFS"),
    ("invesco",    "wd1", "Invesco",                   "Invesco"),
    ("hines",      "wd1", "hines",                     "Hines"),
]

WORKDAY_HEADERS = {
    **HEADERS,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

KEYWORDS = [
    "real estate",
    "acquisitions",
    "underwriting",
    "investment analyst",
    "financial model",
    "valuation",
    "asset management",
    "private equity",
]


def fetch_all(client):
    all_jobs = []
    for tenant, dc, site_id, friendly in WORKDAY_COMPANIES:
        company_jobs = 0
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
                        "id": f"wd-{tenant}-{site_id}-{jid}",
                        "title": title,
                        "company": friendly,
                        "location": loc,
                        "posted": posted,
                        "url": f"https://{tenant}.{dc}.myworkdayjobs.com/{site_id}{ext_url}",
                        "jd_url": f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site_id}/job{ext_url}",
                        "source": "Workday",
                    })
                    company_jobs += 1
            except Exception:
                pass
        print(f"    [wd:{tenant}/{site_id}] {company_jobs} jobs", flush=True)
    # Dedupe (same job may surface for multiple keywords)
    seen_ids = set()
    unique = []
    for j in all_jobs:
        if j["id"] in seen_ids:
            continue
        seen_ids.add(j["id"])
        unique.append(j)
    return unique
