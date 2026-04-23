import os
import httpx
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

INDIA_HINTS = [
    "india",
    "mumbai", "bombay", "bengaluru", "bangalore", "hyderabad", "pune", "gurgaon",
    "gurugram", "noida", "delhi", "new delhi", "ncr", "chennai", "kolkata",
    "ahmedabad", "jaipur", "kochi", "cochin", "indore", "thane", "navi mumbai",
    "maharashtra", "karnataka", "telangana", "tamil nadu", "uttar pradesh",
    "haryana", "gujarat", "rajasthan", "west bengal", "kerala",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# 86400 = 24 hours
TIME_WINDOW_SECONDS = 86400

SEEN_FILE = "seen_jobs.txt"
# How long to keep entries in the seen file (seconds). 7 days = plenty.
SEEN_TTL_SECONDS = 7 * 24 * 3600


def load_seen():
    """Returns a dict: {job_id: timestamp_when_added}"""
    seen = {}
    if not os.path.exists(SEEN_FILE):
        return seen
    now = int(time.time())
    with open(SEEN_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            try:
                job_id, ts = line.split(",", 1)
                ts = int(ts)
                # Skip entries older than TTL (housekeeping)
                if now - ts < SEEN_TTL_SECONDS:
                    seen[job_id] = ts
            except ValueError:
                continue
    return seen


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        for job_id, ts in seen.items():
            f.write(f"{job_id},{ts}\n")


def build_url(query):
    params = {"keywords": query, "f_TPR": f"r{TIME_WINDOW_SECONDS}", "sortBy": "DD"}
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


def passes_title_filter(job):
    title_lower = job["title"].lower()
    if not any(kw in title_lower for kw in INCLUDE_KEYWORDS):
        return False
    if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
        return False
    return True


def passes_location_filter(job):
    loc = job["location"].lower()
    if any(h in loc for h in INDIA_HINTS):
        return True
    is_remote = "remote" in loc
    is_hybrid = "hybrid" in loc
    if is_remote and not is_hybrid:
        return True
    return False


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
        r = httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true",
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"  Telegram send error: {e}", flush=True)
        return False


def run_once():
    seen = load_seen()
    print(f"Loaded {len(seen)} previously-seen job ids", flush=True)

    total_scanned = 0
    total_title_matched = 0
    total_location_matched = 0
    total_alerted = 0
    total_failed = 0
    now = int(time.time())

    with httpx.Client() as client:
        for query in SEARCH_QUERIES:
            jobs = fetch_jobs_for_query(query, client)
            total_scanned += len(jobs)
            for job in jobs:
                if job["id"] in seen:
                    continue
                if not passes_title_filter(job):
                    continue
                total_title_matched += 1
                if not passes_location_filter(job):
                    continue
                total_location_matched += 1
                success = send_telegram(job)
                if success:
                    seen[job["id"]] = now
                    total_alerted += 1
                    print(f"  ✅ {job['title']} @ {job['company']} — {job['location']}", flush=True)
                else:
                    total_failed += 1
                time.sleep(1)
            time.sleep(3)

    save_seen(seen)
    print(f"Scanned {total_scanned}, title-matched {total_title_matched}, "
          f"location-matched {total_location_matched}, "
          f"alerted {total_alerted}, failed {total_failed}, "
          f"seen-file now has {len(seen)} ids", flush=True)


if __name__ == "__main__":
    run_once()
