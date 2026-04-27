import time
import urllib.parse
from common import HEADERS

# Naukri's unofficial API endpoint
NAUKRI_API = "https://www.naukri.com/jobapi/v3/search"

NAUKRI_HEADERS = {
    **HEADERS,
    "Accept": "application/json",
    "appid": "109",
    "systemid": "Naukri",
    "Referer": "https://www.naukri.com/",
}

SEARCHES = [
    "real estate analyst",
    "real estate associate",
    "acquisitions analyst",
    "real estate underwriter",
    "real estate private equity",
    "real estate investment",
    "real estate finance",
    "asset management analyst",
    "portfolio analyst",
    "investment analyst",
    "financial modeling",
    "financial modelling",
    "valuation analyst",
    "argus analyst",
    "reit analyst",
]


def fetch_all(client):
    all_jobs = []
    for keyword in SEARCHES:
        params = {
            "noOfResults": "20",
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": keyword,
            "sort": "f",  # freshness
            "k": keyword,
        }
        url = NAUKRI_API + "?" + urllib.parse.urlencode(params)
        try:
            r = client.get(url, headers=NAUKRI_HEADERS)
            if r.status_code != 200:
                print(f"    [naukri:{keyword}] status {r.status_code}", flush=True)
                continue
            data = r.json()
            for job in data.get("jobDetails", []):
                job_id = str(job.get("jobId", ""))
                if not job_id:
                    continue
                title = job.get("title", "")
                company = job.get("companyName", "?")
                # location can be a list of dicts
                locs = job.get("placeholders", [])
                loc_str = "?"
                for p in locs:
                    if p.get("type") == "location":
                        loc_str = p.get("label", "?")
                        break
                jd_url = "https://www.naukri.com" + job.get("jdURL", "")
                all_jobs.append({
                    "id": f"naukri-{job_id}",
                    "title": title,
                    "company": company,
                    "location": loc_str,
                    "posted": job.get("footerPlaceholderLabel", "recent"),
                    "url": jd_url,
                    "jd_url": jd_url,
                    "source": "Naukri",
                })
        except Exception as e:
            print(f"    [naukri:{keyword}] error: {e}", flush=True)
        time.sleep(2)
    return all_jobs
