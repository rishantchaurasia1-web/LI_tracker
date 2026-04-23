import os
import httpx
import sqlite3
import time
import urllib.parse
import re
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SEARCH_QUERIES = [
    "real estate analyst",
    "real estate associate",
    "acquisitions analyst",
    "real estate underwriter",
    "real estate capital markets",
    "real estate private equity",
]

INCLUDE_KEYWORDS = [
    "commercial real estate analyst", "cre analyst", "real estate financial analyst",
    "real estate acquisitions analyst", "acquisitions analyst", "acquisitions associate",
    "real estate investment analyst", "real estate underwriter", "underwriting analyst",
    "real estate analyst",
    "asset management analyst", "real estate asset manager", "portfolio analyst",
    "fund analyst", "investment management analyst",
    "capital markets analyst", "real estate private equity", "repe analyst",
    "real estate debt analyst", "real estate credit analyst", "commercial mortgage analyst",
    "cmbs analyst", "real estate finance analyst", "real estate lending analyst",
    "real estate valuation analyst", "valuation analyst", "real estate research analyst",
    "market research analyst", "reit analyst", "due diligence analyst",
    "property analyst", "real estate strategy analyst",
    "real estate development analyst", "development analyst", "real estate transaction analyst",
    "investments associate", "land acquisition analyst", "site acquisition analyst",
    "real estate associate",
    "multifamily", "office acquisitions", "retail real estate", "industrial real estate",
    "mixed use development", "hospitality real estate", "healthcare real estate",
    "net lease", "triple net", "self storage",
    "real assets analyst", "private markets analyst", "alternative investments",
    "infrastructure analyst", "institutional investment analyst", "junior investment analyst",
    "financial analyst",
]

EXCLUDE_KEYWORDS = [
    "senior", "sr.", "sr ", "lead", "principal", "director", "vp", "vice president",
    "head of", "head,", "chief", "managing director", "manager", "svp", "evp",
    "intern", "internship", "trainee", "apprentice", "graduate program", "entry level",
    "fresher", "co-op", "coop",
    "sales", "leasing agent", "broker assistant", "receptionist",
]

TARGET_COMPANIES = [
    "cbre", "jll", "cushman", "wakefield", "colliers", "marcus & millichap", "newmark",
    "blackstone", "brookfield", "ares", "kkr", "starwood", "hines", "prologis", "pgim",
    "equity residential", "avalonbay", "simon property", "welltower", "digital realty",
    "wells fargo", "goldman sachs", "morgan stanley", "jpmorgan", "j.p. morgan",
    "walker & dunlop",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

DB_PATH = "jobs_seen.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS seen (job_id TEXT PRIMARY KEY, seen_at INTEGER)")
    conn.commit()
    return conn


def build_url(query):
    params = {"keywords": query, "f_TPR": "r3600", "sortBy": "DD"}
    return "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(params)


def fetch_jobs_for_query(query, client):
    try:
        r = client.get(build_url(query), headers=HEADERS, timeout=20, follow_redirects=True)
        if r.status_code != 200:
            print(f"  [{query}] status {r.status_code}", flush=True)
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = []
        for card in soup.select("div.base-card, li"):
            link_tag = card.select_one("a.base-card__full-link")
            title_tag = card.select_one("h3.base-search-card__title")
            company_tag = card.select_one("h4.base-search-card__subtitle")
            location_tag = card.select_one("span.job-search-card__location")
            time_tag = card.select_one("time")
            if not link_tag or not title_tag:
                continue
            url = link_tag.get("href", "").split("?")[0]
            if not url:
                continue
            match = re.search(r"(\d{8,})", url)
            if not match:
                continue
            job_id = match.group(1)
            jobs.append({
                "id": job_id,
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "?",
                "location": location_tag.get_text(strip=True) if location_tag else "?",
                "posted": time_tag.get_text(strip=True) if time_tag else "just now",
                "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            })
        return jobs
    except Exception as e:
        print(f"  [{query}] error: {e}", flush=True)
        return []


def passes_filters(job):
    title_lower = job["title"].lower()
    if not any(kw in title_lower for kw in INCLUDE_KEYWORDS):
        return False
    if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
        return False
    return True


def is_target_company(company_name):
    c = company_name.lower()
    return any(tc in c for tc in TARGET_COMPANIES)


def send_telegram(job):
    star = "⭐ " if is_target_company(job["company"]) else ""
    text = (
        f"🎯 {star}*{job['title']}*\n"
        f"🏢 {job['company']}\n"
        f"📍 {job['location']}\n"
        f"⏱️ {job['posted']}\n\n"
        f"[Apply now →]({job['url']})"
    )
    try:
        httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"  Telegram send error: {e}", flush=True)


def run_once():
    conn = init_db()
    total_seen = 0
    total_matched = 0
    total_alerted = 0
    with httpx.Client() as client:
        for query in SEARCH_QUERIES:
            jobs = fetch_jobs_for_query(query, client)
            total_seen += len(jobs)
            for job in jobs:
                if not passes_filters(job):
                    continue
                total_matched += 1
                cur = conn.execute("SELECT 1 FROM seen WHERE job_id = ?", (job["id"],))
                if cur.fetchone():
                    continue
                send_telegram(job)
                conn.execute(
                    "INSERT INTO seen (job_id, seen_at) VALUES (?, ?)",
                    (job["id"], int(time.time())),
                )
                conn.commit()
                total_alerted += 1
                time.sleep(1)
            time.sleep(3)
    print(f"Scanned {total_seen}, matched {total_matched}, new alerts {total_alerted}", flush=True)


if __name__ == "__main__":
    run_once()
