"""
Adzuna API scraper. Free aggregator that indexes Naukri, Monster, TimesJobs,
Shine, and other Indian sites.

Free tier: 250 calls/day, 25/min. We use ~20-40/day.
Endpoint: https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
Country codes: in=India, us=USA, gb=UK
"""
import os
import time
from common import HEADERS

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")

# Search query plans: (country_code, keyword, location_or_blank)
# Each entry = 1 API call. Stay well under 250/day across all runs.
# Current setup: ~20 calls per run → at */15 cron = ~1920/day → TOO MANY
# Solution: only call Adzuna every 4th run (effectively every hour)
# Implemented via the run_id check below.

INDIA_QUERIES = [
    "real estate analyst",
    "acquisitions analyst",
    "real estate associate",
    "real estate underwriter",
    "real estate finance",
    "real estate investment",
    "asset management analyst",
    "investment analyst",
    "financial modeling",
    "financial modelling",
    "valuation analyst",
    "real estate private equity",
    "argus analyst",
    "reit analyst",
    "real estate fund",
]

US_QUERIES = [
    "real estate analyst remote",
    "acquisitions analyst remote",
    "financial modeling remote",
]


def _should_run_this_cycle():
    """Only run Adzuna every ~4th cron tick to stay under quota.
    Uses minute of the hour as a cheap rotor — runs only when minute < 15.
    With */15 cron, that's roughly once per hour."""
    import datetime
    minute = datetime.datetime.utcnow().minute
    return minute < 15


def _call(client, country, keyword, where=""):
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": 30,
        "what": keyword,
        "max_days_old": 7,
        "sort_by": "date",
        "content-type": "application/json",
    }
    if where:
        params["where"] = where
    try:
        r = client.get(url, params=params, headers=HEADERS)
        if r.status_code != 200:
            print(f"    [adzuna:{country}:{keyword[:30]}] status {r.status_code}", flush=True)
            return []
        data = r.json()
        return data.get("results", [])
    except Exception as e:
        print(f"    [adzuna:{country}:{keyword[:30]}] error: {e}", flush=True)
        return []


def fetch_all(client):
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("    [adzuna] no credentials in env — skipping", flush=True)
        return []

    if not _should_run_this_cycle():
        print("    [adzuna] not this cycle (rate budgeting) — skipping", flush=True)
        return []

    all_jobs = []

    # India queries (no `where` — covers all India)
    for kw in INDIA_QUERIES:
        for raw in _call(client, "in", kw):
            jid = str(raw.get("id", ""))
            if not jid:
                continue
            company = (raw.get("company") or {}).get("display_name", "?")
            loc = (raw.get("location") or {}).get("display_name", "?")
            desc = (raw.get("description") or "").lower()
            all_jobs.append({
                "id": f"adz-in-{jid}",
                "title": raw.get("title", ""),
                "company": company,
                "location": loc,
                "posted": (raw.get("created", "") or "")[:10] or "recent",
                "url": raw.get("redirect_url", ""),
                "jd_text": desc,  # adzuna returns description snippet, no extra fetch
                "source": "Adzuna-IN",
            })
        time.sleep(3)  # respect 25/min

    # US queries (remote)
    for kw in US_QUERIES:
        for raw in _call(client, "us", kw):
            jid = str(raw.get("id", ""))
            if not jid:
                continue
            company = (raw.get("company") or {}).get("display_name", "?")
            loc = (raw.get("location") or {}).get("display_name", "?")
            desc = (raw.get("description") or "").lower()
            all_jobs.append({
                "id": f"adz-us-{jid}",
                "title": raw.get("title", ""),
                "company": company,
                "location": loc,
                "posted": (raw.get("created", "") or "")[:10] or "recent",
                "url": raw.get("redirect_url", ""),
                "jd_text": desc,
                "source": "Adzuna-US",
            })
        time.sleep(3)

    print(f"    [adzuna] {len(all_jobs)} total jobs across {len(INDIA_QUERIES)+len(US_QUERIES)} queries", flush=True)
    return all_jobs
