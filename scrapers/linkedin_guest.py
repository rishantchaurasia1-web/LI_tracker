import re
import time
import random
import urllib.parse
from bs4 import BeautifulSoup
from common import HEADERS

TIME_WINDOW_SECONDS = 86400

SEARCHES = [
    # India — all workplace types
    ("real estate analyst", "India", None),
    ("real estate associate", "India", None),
    ("acquisitions analyst", "India", None),
    ("acquisitions associate", "India", None),
    ("real estate underwriter", "India", None),
    ("underwriting analyst", "India", None),
    ("real estate capital markets", "India", None),
    ("real estate private equity", "India", None),
    ("asset management analyst", "India", None),
    ("portfolio analyst", "India", None),
    ("real estate investment", "India", None),
    ("real estate finance", "India", None),
    ("real estate valuation", "India", None),
    ("real estate development", "India", None),
    ("reit analyst", "India", None),
    ("investment analyst", "India", None),
    ("financial analyst real estate", "India", None),
    # Financial modeling — NEW
    ("financial modeling", "India", None),
    ("financial modeller", "India", None),
    ("valuation analyst", "India", None),
    ("lbo modeling", "India", None),
    ("argus modeling", "India", None),
    ("waterfall modeling", "India", None),
    # US remote
    ("real estate analyst", "United States", "2"),
    ("acquisitions analyst", "United States", "2"),
    ("real estate underwriter", "United States", "2"),
    ("financial modeling", "United States", "2"),
    # Global remote
    ("real estate analyst", "", "2"),
    ("acquisitions analyst", "", "2"),
    ("financial modeling", "", "2"),
]

DELAY_BETWEEN_SEARCHES = 4


def build_url(keyword, location, remote_filter):
    params = {"keywords": keyword, "f_TPR": f"r{TIME_WINDOW_SECONDS}", "sortBy": "DD"}
    if location:
        params["location"] = location
    if remote_filter:
        params["f_WT"] = remote_filter
    return ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
            + urllib.parse.urlencode(params))


def parse_jobs(html):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for card in soup.select("div.base-card, li"):
        link = card.select_one("a.base-card__full-link")
        title = card.select_one("h3.base-search-card__title")
        company = card.select_one("h4.base-search-card__subtitle")
        loc = card.select_one("span.job-search-card__location")
        time_tag = card.select_one("time")
        if not link or not title:
            continue
        url = link.get("href", "").split("?")[0]
        if not url:
            continue
        m = re.search(r"(\d{8,})", url)
        if not m:
            continue
        job_id = m.group(1)
        jobs.append({
            "id": f"li-{job_id}",
            "title": title.get_text(strip=True),
            "company": company.get_text(strip=True) if company else "?",
            "location": loc.get_text(strip=True) if loc else "?",
            "posted": time_tag.get_text(strip=True) if time_tag else "just now",
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            "jd_url": f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}",
            "source": "LinkedIn",
        })
    return jobs


def fetch_all(client):
    all_jobs = []
    shuffled = list(SEARCHES)
    random.shuffle(shuffled)
    for keyword, location, remote in shuffled:
        label = f"{keyword} | {location or 'Global'} | {'Remote' if remote else 'Any'}"
        try:
            r = client.get(build_url(keyword, location, remote), headers=HEADERS)
            if r.status_code != 200:
                print(f"    [{label}] status {r.status_code}", flush=True)
                continue
            jobs = parse_jobs(r.text)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"    [{label}] error: {e}", flush=True)
        time.sleep(DELAY_BETWEEN_SEARCHES)
    # dedupe by id
    seen_ids = set()
    unique = []
    for j in all_jobs:
        if j["id"] in seen_ids:
            continue
        seen_ids.add(j["id"])
        unique.append(j)
    return unique
