import os
import httpx
import time
import urllib.parse
import re
import random
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# (keyword, location, remote_filter). f_WT=2 = remote only. None = any mode.
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
    ("repe analyst", "India", None),
    ("asset management analyst", "India", None),
    ("portfolio analyst", "India", None),
    ("real estate investment", "India", None),
    ("real estate finance", "India", None),
    ("real estate valuation", "India", None),
    ("real estate research", "India", None),
    ("real estate development", "India", None),
    ("real estate fund", "India", None),
    ("reit analyst", "India", None),
    ("real assets analyst", "India", None),
    ("private markets analyst", "India", None),
    ("investment analyst", "India", None),
    ("financial analyst real estate", "India", None),
    ("cre analyst", "India", None),
    # US remote
    ("real estate analyst", "United States", "2"),
    ("real estate associate", "United States", "2"),
    ("acquisitions analyst", "United States", "2"),
    ("real estate underwriter", "United States", "2"),
    ("real estate private equity", "United States", "2"),
    ("asset management analyst", "United States", "2"),
    # Global remote
    ("real estate analyst", "", "2"),
    ("acquisitions analyst", "", "2"),
    ("real estate private equity", "", "2"),
    ("real estate associate", "", "2"),
    ("real estate underwriter", "", "2"),
]

# Path A: any of these as a substring in title = direct match
INCLUDE_KEYWORDS = [
    "real estate analyst", "commercial real estate analyst", "cre analyst",
    "real estate financial analyst", "real estate investment analyst",
    "real estate acquisitions analyst", "acquisitions analyst",
    "underwriting analyst", "real estate underwriter",
    "real estate credit analyst", "real estate debt analyst",
    "real estate equity analyst", "real estate finance analyst",
    "real estate valuation analyst", "real estate due diligence analyst",
    "real estate research analyst", "real estate market analyst",
    "real estate portfolio analyst", "real estate asset management analyst",
    "real estate fund analyst", "real estate capital markets analyst",
    "real estate transaction analyst", "real estate development analyst",
    "real estate strategy analyst", "real estate structured finance analyst",
    "real estate mortgage analyst", "commercial mortgage analyst", "cmbs analyst",
    "real estate securities analyst", "real estate risk analyst",
    "real estate compliance analyst", "real estate reporting analyst",
    "real estate budget analyst", "real estate operations analyst",
    "real estate investment management analyst", "real estate lending analyst",
    "real estate originations analyst", "real estate disposition analyst",
    "real estate joint venture analyst", "real estate lease analyst",
    "real estate asset analyst", "real estate property analyst",
    "real estate feasibility analyst", "real estate mixed use analyst",
    "real estate land analyst", "land acquisition analyst", "site acquisition analyst",
    "multifamily analyst", "multifamily acquisitions", "multifamily underwriting",
    "multifamily investment", "office real estate analyst",
    "retail real estate analyst", "industrial real estate analyst",
    "hospitality real estate analyst", "healthcare real estate analyst",
    "senior housing analyst", "net lease analyst", "triple net analyst",
    "self storage analyst", "data center real estate", "student housing analyst",
    "affordable housing analyst", "workforce housing analyst",
    "real estate associate", "acquisitions associate",
    "investment associate real estate", "real estate finance associate",
    "asset management associate", "real estate capital markets associate",
    "real estate private equity associate", "repe associate",
    "real estate development associate", "real estate underwriting associate",
    "real estate research associate", "real estate transaction associate",
    "real estate portfolio associate", "real estate debt associate",
    "real estate equity associate", "real estate structured finance associate",
    "real estate investment associate", "real estate lending associate",
    "real estate originations associate", "real estate joint venture associate",
    "real estate asset management associate", "real estate fund associate",
    "real estate valuation associate", "real estate due diligence associate",
    "real estate credit associate",
    "real estate private equity", "repe analyst", "real estate fund",
    "private real estate analyst", "real estate alternatives analyst",
    "real assets analyst", "real assets associate",
    "private markets analyst", "institutional real estate analyst",
    "real estate lp analyst", "real estate gp analyst",
    "real estate equity fund", "real estate debt fund",
    "real estate core fund", "real estate value add",
    "real estate opportunistic", "real estate mezzanine",
    "real estate preferred equity",
    "real estate asset manager", "asset management analyst",
    "real estate portfolio manager", "portfolio analyst",
    "real estate investment manager", "real estate performance analyst",
    "real estate waterfall analyst", "real estate returns analyst",
    "real estate noi analyst", "real estate cash flow analyst",
    "development finance analyst", "real estate project finance",
    "real estate construction finance", "real estate proforma",
    "real estate land development", "real estate entitlement",
    "real estate pre development", "real estate mixed use development",
    "real estate ground up development", "real estate repositioning",
    "commercial real estate lending", "cre lending analyst",
    "real estate loan analyst", "real estate underwriter debt",
    "real estate bridge loan", "real estate construction loan",
    "real estate structured debt", "real estate loan underwriter",
    "real estate agency lending", "freddie mac", "fannie mae",
    "fha multifamily", "real estate conduit loan",
    "real estate balance sheet lending", "real estate syndicated loan",
    "real estate investment sales", "real estate equity placement",
    "real estate debt placement", "real estate securitization",
    "real estate capital raise", "real estate investor relations",
    "real estate lp relations", "real estate syndication",
    "real estate appraisal", "real estate mai analyst",
    "real estate dcf", "real estate discounted cash flow",
    "real estate cap rate", "real estate mark to market",
    "real estate nav analyst", "real estate fair value",
    "argus analyst",
    "real estate market research", "real estate economics",
    "real estate forecasting", "real estate data analyst",
    "real estate intelligence", "real estate trends",
    "real estate sector analyst", "reit analyst",
    "real estate equity research",
    "real estate accounting analyst", "real estate financial reporting",
    "real estate fund accounting", "real estate tax analyst",
    "real estate audit analyst", "real estate fp&a",
    "real estate financial planning", "real estate treasury",
    "property finance analyst", "real estate leasing finance",
    "real estate lease administration", "real estate revenue analyst",
    "real estate operating budget", "real estate capital expenditure",
    "real estate capex", "real estate property performance",
    "proptech analyst", "real estate technology analyst",
    "real estate esg analyst", "real estate sustainability",
    "real estate impact investing", "real estate opportunity zone",
    "real estate 1031", "real estate tax credit", "lihtc analyst",
    "real estate infrastructure", "real estate special situations",
    "real estate distressed", "real estate workout",
    "real estate npl", "real estate reo",
    "financial analyst", "investment analyst", "private equity analyst",
    "investment banking analyst",
]

# Hard-block titles regardless of other matches
EXCLUDE_KEYWORDS = [
    "director", "vp", "vice president", "head of", "head,",
    "chief", "managing director", "svp", "evp", "president",
    "intern", "internship", "trainee", "apprentice", "graduate program",
    "fresher", "co-op", "coop",
    "sales representative", "leasing agent", "broker assistant", "receptionist",
    "administrative assistant", "executive assistant",
]

# For Path B: title must have at least one of these "finance-adjacent" words
# to justify a JD fetch (prevents JD-checking software engineer jobs)
PATH_B_TITLE_HINTS = [
    "analyst", "associate", "investment", "finance", "financial",
    "portfolio", "capital", "fund", "credit", "debt", "equity",
    "underwriter", "underwriting", "valuation", "acquisitions",
    "research", "strategy", "advisory", "consulting",
]

# Target companies — brand names only (no "India", "Real Estate", "Group" etc.)
# Case-insensitive substring match against LinkedIn's company name.
TARGET_COMPANIES = [
    # Private Equity & Investment Management
    "blackstone", "brookfield", "starwood", "fortress investment",
    "cerberus capital", "apollo global", "ares management",
    "kkr", "carlyle", "warburg pincus", "oaktree",
    "angelo gordon", "lone star funds", "tpg", "benefit street",
    "amherst", "pretium", "greystar", "cortland",
    "invesco", "pgim", "nuveen", "principal real estate",
    "metlife investment", "prudential real estate", "tiaa",
    "clarion partners", "heitman", "cornerstone real estate",
    "lasalle investment", "bentall greenoak", "greenoak",
    "lionstone", "waterton", "stockbridge",
    "hamilton lane", "kayne anderson",
    # REITs & Operating
    "prologis", "digital realty", "equinix", "cbre investment",
    "hines", "tishman speyer", "related companies", "vornado",
    "boston properties", "sl green", "mack-cali",
    "cousins properties", "highwoods", "brandywine",
    "piedmont office",
    # Debt & Lending
    "walker & dunlop", "walker and dunlop", "arbor realty",
    "ready capital", "ladder capital", "mesa west",
    "torchlight", "owl rock", "blue owl",
    # Advisory & Brokerage
    "cbre", "jll", "cushman", "wakefield", "colliers",
    "newmark", "marcus & millichap", "savills",
    "knight frank", "eastdil", "berkadia", "avison young",
    # UK/European
    "bnp paribas real estate", "axa im", "allianz real estate",
    "union investment", "deka immobilien", "dws",
    "aberdeen standard", "schroders", "patrizia",
    "tristan capital", "round hill capital",
    # APAC
    "gic", "mapletree", "capitaland", "ascendas",
    "keppel", "frasers property", "esr", "pag real estate",
    "gaw capital", "cppib", "cdpq", "oxford properties",
    "quadreal", "ivanhoe cambridge", "ivanhoé",
    "manulife real estate", "sumitomo real estate",
    "mitsubishi estate", "tokyu land", "lendlease",
    "dexus", "charter hall",
    # Indian Developers
    "dlf", "godrej properties", "oberoi realty", "prestige estates",
    "brigade enterprises", "sobha", "mahindra lifespace",
    "lodha", "macrotech", "puravankara", "kolte patil",
    "shapoorji pallonji", "tata realty", "embassy",
    "hiranandani", "raheja", "phoenix mills",
    "sunteck", "keystone realtors", "rustomjee",
    "nirlon", "nesco", "equinox india",
    "omaxe", "db realty", "indiabulls real estate", "ansal api",
    # Indian RE PE / Funds
    "piramal fund", "kotak realty", "hdfc capital",
    "ask property", "motilal oswal real estate",
    "edelweiss alternatives", "360 one", "icici prudential real estate",
    "sundaram alternates", "centrum real estate",
    "xander", "indospace", "indiareit",
    "milestone capital", "altico", "investcorp",
    # Indian NBFC & RE Lending
    "piramal housing", "hdfc limited", "lic housing",
    "indiabulls housing", "pnb housing", "bajaj housing",
    "aadhar housing", "can fin homes", "gic housing finance",
    "repco home", "india shelter", "aavas",
    "home first finance", "aptus value", "shriram housing",
    "tata capital housing", "l&t finance", "godrej housing",
    "aditya birla housing", "icici home", "kotak mahindra prime",
    # Indian REITs
    "embassy office parks", "mindspace business parks",
    "brookfield india real estate", "nexus select",
    # Logistics
    "welspun one", "logos india", "embassy industrial",
    "glp india", "stellar value chain",
    # IBs
    "goldman sachs", "morgan stanley", "jpmorgan",
    "j.p. morgan", "bank of america", "citibank", "citi",
    "barclays", "deutsche bank", "credit suisse",
    "standard chartered", "hsbc", "nomura", "ubs",
    "jefferies", "rbc capital", "wells fargo",
    # Big 4 & Consulting
    "deloitte", "pwc", "ernst & young", " ey ", "kpmg",
    "mckinsey", "bcg", "bain", "grant thornton",
    "rsm", "bdo",
]

INDIA_HINTS = [
    "india",
    "mumbai", "bombay", "bengaluru", "bangalore", "hyderabad", "pune",
    "delhi", "new delhi", "ncr", "gurgaon", "gurugram", "noida", "ghaziabad", "faridabad",
    "chennai", "madras", "kolkata", "calcutta",
    "ahmedabad", "jaipur", "kochi", "cochin", "ernakulam", "indore",
    "thane", "navi mumbai", "lucknow", "kanpur", "nagpur", "bhopal",
    "surat", "vadodara", "baroda", "chandigarh", "mohali", "panchkula",
    "dehradun", "raipur", "ranchi", "bhubaneswar", "visakhapatnam", "vizag",
    "coimbatore", "madurai", "trichy", "tiruchirappalli",
    "thiruvananthapuram", "trivandrum", "kozhikode", "calicut",
    "mysore", "mysuru", "mangalore", "mangaluru",
    "hubli", "hubballi", "belgaum", "belagavi",
    "guwahati", "patna", "varanasi", "allahabad", "prayagraj",
    "agra", "meerut", "amritsar", "ludhiana", "jalandhar",
    "jammu", "srinagar", "shimla", "udaipur", "jodhpur",
    "kota", "ajmer", "aurangabad", "nashik", "solapur", "kolhapur",
    "siliguri", "asansol", "durgapur", "bhilai", "jamshedpur", "dhanbad",
    "goa", "panaji", "margao", "vasco", "puducherry", "pondicherry",
    "maharashtra", "karnataka", "telangana", "tamil nadu", "uttar pradesh",
    "haryana", "gujarat", "rajasthan", "west bengal", "kerala",
    "andhra pradesh", "madhya pradesh", "bihar", "odisha", "orissa",
    "punjab", "himachal pradesh", "uttarakhand", "jharkhand", "chhattisgarh",
    "assam", "meghalaya", "manipur", "tripura", "nagaland", "mizoram",
    "arunachal pradesh", "sikkim", "jammu and kashmir", "ladakh",
    "andaman", "lakshadweep",
]

# JD must mention at least one of these to pass Path B
JD_MUST_CONTAIN = [
    "real estate", "commercial real estate", " cre ",
    "repe", "reit", "reits",
    "alternative investment", "alternative investments", "alternatives",
    "private markets", "private equity real estate",
    "multi-asset", "multi asset", "multiple asset classes",
    "real assets", "infrastructure fund", "direct real estate",
    "property investment", "property fund", "realty",
    "aum", "institutional investor", "institutional investors",
    "asset management firm", "amc", "asset management company",
    "multifamily", "industrial real estate", "office real estate",
    "retail real estate", "hospitality real estate",
    "cmbs", "mortgage-backed", "mortgage backed",
    "cap rate", "noi ", "argus", "dcf", "underwriting",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

TIME_WINDOW_SECONDS = 86400
MAX_JD_FETCHES_PER_RUN = 15
DELAY_BETWEEN_SEARCHES = 5
DELAY_BETWEEN_JOBS = 1

SEEN_FILE = "seen_jobs.txt"
SEEN_TTL_SECONDS = 2 * 24 * 3600


def load_seen():
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
                if now - ts < SEEN_TTL_SECONDS:
                    seen[job_id] = ts
            except ValueError:
                continue
    return seen


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        for job_id, ts in seen.items():
            f.write(f"{job_id},{ts}\n")


def build_url(keyword, location, remote_filter):
    params = {"keywords": keyword, "f_TPR": f"r{TIME_WINDOW_SECONDS}", "sortBy": "DD"}
    if location:
        params["location"] = location
    if remote_filter:
        params["f_WT"] = remote_filter
    return "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(params)


def fetch_jobs(keyword, location, remote_filter, client):
    label = f"{keyword} | {location or 'Global'} | {'Remote' if remote_filter else 'Any'}"
    try:
        r = client.get(build_url(keyword, location, remote_filter), headers=HEADERS, timeout=20, follow_redirects=True)
        if r.status_code != 200:
            print(f"  [{label}] status {r.status_code}", flush=True)
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
            m = re.search(r"(\d{8,})", url)
            if not m:
                continue
            job_id = m.group(1)
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
        print(f"  [{label}] error: {e}", flush=True)
        return []


def title_has_excludes(job):
    t = job["title"].lower()
    return any(kw in t for kw in EXCLUDE_KEYWORDS)


def title_has_includes(job):
    t = job["title"].lower()
    return any(kw in t for kw in INCLUDE_KEYWORDS)


def title_has_path_b_hint(job):
    t = job["title"].lower()
    return any(h in t for h in PATH_B_TITLE_HINTS)


def is_target_company(company_name):
    c = company_name.lower()
    return any(tc in c for tc in TARGET_COMPANIES)


def passes_location_filter(job):
    loc = job["location"].lower()
    if any(h in loc for h in INDIA_HINTS):
        return True
    is_remote = "remote" in loc
    is_hybrid = "hybrid" in loc
    return is_remote and not is_hybrid


def fetch_job_description(job_id, client):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        r = client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        desc = soup.select_one("div.show-more-less-html__markup, div.description__text")
        return desc.get_text(" ", strip=True).lower() if desc else ""
    except Exception:
        return ""


def jd_mentions_re(job_id, client):
    jd = fetch_job_description(job_id, client)
    if not jd:
        return False
    return any(term in jd for term in JD_MUST_CONTAIN)


def send_telegram(job, reason):
    star = "⭐ " if is_target_company(job["company"]) else ""
    tag = f"_{reason}_\n"
    text = (
        f"🎯 {star}*{job['title']}*\n"
        f"🏢 {job['company']}\n"
        f"📍 {job['location']}\n"
        f"⏱️ {job['posted']}\n"
        f"{tag}\n"
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

    scanned = matched = alerted = failed = 0
    jd_fetches = 0

    with httpx.Client() as client:
        shuffled = list(SEARCHES)
        random.shuffle(shuffled)
        for keyword, location, remote_filter in shuffled:
            jobs = fetch_jobs(keyword, location, remote_filter, client)
            scanned += len(jobs)
            for job in jobs:
                if job["id"] in seen:
                    continue

                # Hard exclude (director, VP, intern etc.) — never pass
                if title_has_excludes(job):
                    continue

                # Location filter applies to EVERYONE
                if not passes_location_filter(job):
                    continue

                is_target = is_target_company(job["company"])
                title_match = title_has_includes(job)
                reason = None

                # Path A: Title directly matches → pass, no JD
                if title_match:
                    reason = "title match"
                # Target company: JD-check even with odd titles (skip path B pre-filter)
                elif is_target:
                    if jd_fetches < MAX_JD_FETCHES_PER_RUN:
                        jd_fetches += 1
                        if jd_mentions_re(job["id"], client):
                            reason = "target co. + JD match"
                # Path B: Non-target co, title has analyst-like word, check JD
                elif title_has_path_b_hint(job):
                    if jd_fetches < MAX_JD_FETCHES_PER_RUN:
                        jd_fetches += 1
                        if jd_mentions_re(job["id"], client):
                            reason = "JD match"

                if reason is None:
                    continue

                matched += 1
                success = send_telegram(job, reason)
                if success:
                    seen[job["id"]] = int(time.time())
                    alerted += 1
                    print(f"  ✅ [{reason}] {job['title']} @ {job['company']} — {job['location']}", flush=True)
                else:
                    failed += 1
                time.sleep(DELAY_BETWEEN_JOBS)
            time.sleep(DELAY_BETWEEN_SEARCHES)
    save_seen(seen)
    print(f"Scanned {scanned}, matched {matched}, alerted {alerted}, failed {failed}, "
          f"JD fetches used {jd_fetches}/{MAX_JD_FETCHES_PER_RUN}, "
          f"seen-file has {len(seen)} ids", flush=True)


if __name__ == "__main__":
    run_once()
