import re
from common import HEADERS

# Verified Greenhouse boards (each confirmed to exist as of writing).
# Format: (board_token, friendly_name)
# To add more: visit https://boards.greenhouse.io/{token} or
# https://job-boards.greenhouse.io/{token} in a browser. If it loads, add it.
GREENHOUSE_COMPANIES = [
    # Real estate operators / investors / advisors
    ("lpc",                    "Lincoln Property Company"),
    ("eqtpartners",            "EQT Partners"),
    ("northmarq",              "Northmarq"),
    ("krollbondratingagency",  "KBRA"),
    ("verticalbridge",         "Vertical Bridge"),
    ("ascentds",               "Ascent Developer Solutions"),
    ("housebuyersofamerica",   "House Buyers of America"),
    ("stepstone",              "StepStone Group"),
    ("icapitalnetwork",        "iCapital"),
    ("gtcr",                   "GTCR"),
    # Proptech / RE-finance / RE-tech
    ("juniper-square",         "Juniper Square"),
    ("vts",                    "VTS"),
    ("cadre",                  "Cadre"),
    ("fundrise",               "Fundrise"),
    ("compass",                "Compass"),
    ("opendoor",               "Opendoor"),
    # Adjacent (financial modeling / IB / PE)
    ("morningstar",            "Morningstar"),
    ("orion-group",            "Orion Group"),
]

# Greenhouse has TWO public API hostnames. New boards use the second.
ENDPOINTS = [
    "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
    "https://api.greenhouse.io/v1/boards/{token}/jobs?content=true",
]


def _strip_html(html_text):
    if not html_text:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def fetch_all(client):
    all_jobs = []
    for token, friendly in GREENHOUSE_COMPANIES:
        data = None
        for url_tpl in ENDPOINTS:
            url = url_tpl.format(token=token)
            try:
                r = client.get(url, headers=HEADERS)
                if r.status_code == 200:
                    data = r.json()
                    break
            except Exception:
                continue
        if not data:
            print(f"    [gh:{token}] no data (maybe board moved)", flush=True)
            continue

        for job in data.get("jobs", []):
            jid = str(job.get("id", ""))
            if not jid:
                continue
            title = job.get("title", "")
            loc = (job.get("location") or {}).get("name", "?")
            jd_text = _strip_html(job.get("content", ""))
            updated = (job.get("updated_at") or "")[:10] or "recent"
            all_jobs.append({
                "id": f"gh-{token}-{jid}",
                "title": title,
                "company": friendly,
                "location": loc,
                "posted": updated,
                "url": job.get("absolute_url", ""),
                "jd_text": jd_text,
                "source": "Greenhouse",
            })
        print(f"    [gh:{token}] {len(data.get('jobs', []))} jobs", flush=True)
    return all_jobs
