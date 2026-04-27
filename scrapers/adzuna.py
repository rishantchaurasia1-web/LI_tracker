"""
Adzuna API scraper. Free aggregator that indexes Naukri, Monster, TimesJobs,
Shine, and other Indian sites.

Free tier: 250 calls/day, 25/min.
Endpoint: https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
"""
import os
import time
from common import HEADERS

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")

# India queries — covers most relevant roles
INDIA_QUERIES = [
    "real estate analyst",
    "acquisitions analyst",
    "real estate associate",
    "real estate underwriter",
    "real estate investment",
    "asset management analyst",
    "investment analyst",
    "financial modeling",
    "valuation analyst",
    "real estate private equity",
    "argus analyst",
    "reit analyst",
]

# US remote — keep small
US_QUERIES = [
    "real estate analyst",
    "acquisitions analyst",
    "financial modeling",
]

# Quota math:
# 15 queries × runs per day. With */15 cron = 96 runs/day.
# That's 1440 calls — way over 250 quota.
# Solution: run only when UTC minute is in [0, 15, 30, 45] AND hour is even
# = 12 runs/day × 15 calls = 180 calls/day. Safe.

def _should_run_this_cycle():
    import datetime
    now = datetime.datetime.utcnow()
    # Run every 2 hours. Hour is even AND minute is in first 15 of the hour.
    return (now.hour % 2 == 0) and (now.minute < 15)


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
        if r.status_code == 401 or r.status_code == 403:
            print(f"    [adzuna] AUTH FAILED — status {r.status_code}. Check ADZUNA_APP_ID/KEY secrets.", flush=True)
            return None  # signal: stop trying
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
        print("    [adzuna] not this cycle (every 2 hours) — skipping", flush=True)
        return []

    print(f"    [adzuna] credentials present, running {len(INDIA_QUERIES)+len(US_QUERIES)} queries", flush=True)
    all_jobs = []
    auth_failed = False

    for kw in INDIA_QUERIES:
        if auth_failed:
            break
        results = _call(client, "in", kw)
        if results is None:
            auth_failed = True
            break
        for raw in results:
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
                "jd_text": desc,
                "source": "Adzuna-IN",
            })
        time.sleep(3)

    for kw in US_QUERIES:
        if auth_failed:
            break
        results = _call(client, "us", kw)
        if results is None:
            auth_failed = True
            break
        for raw in results:
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
                "jd_url": raw.get("redirect_url", ""),
                "jd_text": desc,
                "source": "Adzuna-US",
            })
        time.sleep(3)

    print(f"    [adzuna] {len(all_jobs)} total jobs", flush=True)
    return all_jobs
