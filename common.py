import os
import re
import time
import httpx
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SEEN_FILE = "seen_jobs.txt"
SEEN_TTL_SECONDS = 2 * 24 * 3600

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# ============ INCLUDE keywords (title hits = instant pass) ============
INCLUDE_KEYWORDS = [
    # Real estate analyst/associate (your existing list, kept)
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
    "real estate associate", "acquisitions associate",
    "investment associate real estate", "real estate finance associate",
    "asset management associate", "real estate capital markets associate",
    "real estate private equity associate", "repe associate",
    "real estate development associate", "real estate underwriting associate",
    "real estate private equity", "repe analyst", "real estate fund",
    "real assets analyst", "real assets associate",
    "private markets analyst", "institutional real estate analyst",
    "asset management analyst", "portfolio analyst",
    "argus analyst", "reit analyst",
    # Multifamily / sector-specific
    "multifamily analyst", "multifamily acquisitions", "multifamily underwriting",
    "industrial real estate analyst", "office real estate analyst",
    "retail real estate analyst", "data center real estate",
    "self storage analyst", "student housing analyst",
    "senior housing analyst", "net lease analyst",
    # Financial modeling — NEW
    "financial modeling", "financial modeler", "financial modelling",
    "financial modeller", "financial modeling analyst",
    "financial modelling analyst", "financial modeling associate",
    "valuation analyst", "valuation associate", "valuations analyst",
    "lbo modeling", "dcf modeling", "merger modeling", "m&a modeling",
    "acquisition modeling", "acquisitions modeling",
    "waterfall modeling", "waterfall analyst",
    "private equity modeling", "pe modeling",
    "argus modeling", "argus enterprise",
    "real estate modeling", "real estate modelling", "real estate modeler",
    "infrastructure modeling", "project finance modeling",
    "fp&a modeling", "fpa modeling",
    "scenario modeling analyst", "three statement modeling",
    "deal modeling", "transaction modeling",
    # Generic high-signal titles
    "financial analyst", "investment analyst", "private equity analyst",
    "investment banking analyst",
]

# ============ EXCLUDE keywords (title hits = hard reject) ============
EXCLUDE_KEYWORDS = [
    "director", "vp", "vice president", "head of", "head,",
    "chief", "managing director", "svp", "evp", "president",
    "intern", "internship", "trainee", "apprentice", "graduate program",
    "fresher", "co-op", "coop",
    "sales representative", "leasing agent", "broker assistant", "receptionist",
    "administrative assistant", "executive assistant",
]

# ============ Path B title hints ============
PATH_B_TITLE_HINTS = [
    "analyst", "associate", "investment", "finance", "financial",
    "portfolio", "capital", "fund", "credit", "debt", "equity",
    "underwriter", "underwriting", "valuation", "acquisitions",
    "research", "strategy", "advisory", "consulting",
    "modeling", "modelling", "modeler", "modeller",  # NEW
]

# ============ Target companies ============
TARGET_COMPANIES = [
    # PE & Investment Management
    "blackstone", "brookfield", "starwood", "fortress investment",
    "cerberus capital", "apollo global", "ares management",
    "kkr", "carlyle", "warburg pincus", "oaktree",
    "angelo gordon", "lone star funds", "tpg", "benefit street",
    "amherst", "pretium", "greystar", "cortland",
    "invesco", "pgim", "nuveen", "principal real estate",
    "metlife investment", "prudential real estate", "tiaa",
    "clarion partners", "heitman", "lasalle investment",
    "bentall greenoak", "greenoak", "lionstone", "waterton",
    "stockbridge", "hamilton lane", "kayne anderson",
    # REITs & Operating
    "prologis", "digital realty", "equinix", "cbre investment",
    "hines", "tishman speyer", "related companies", "vornado",
    "boston properties", "sl green", "cousins properties",
    "highwoods", "brandywine", "piedmont office",
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
    "deloitte", "pwc", "ernst & young", "kpmg",
    "mckinsey", "bcg", "bain", "grant thornton",
    "rsm", "bdo",
    # Financial modeling-heavy firms — NEW
    "moelis", "evercore", "lazard", "houlihan lokey",
    "rothschild", "guggenheim", "perella weinberg",
    "centerview", "pjt partners",
    "avendus", "spark capital", "veda corporate", "o3 capital",
    "iifl", "edelweiss", "jm financial", "axis capital",
    "icici securities", "kotak investment banking",
]

INDIA_HINTS = [
    "india",
    "mumbai", "bombay", "bengaluru", "bangalore", "hyderabad", "pune",
    "delhi", "new delhi", "ncr", "gurgaon", "gurugram", "noida",
    "ghaziabad", "faridabad", "chennai", "madras", "kolkata", "calcutta",
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

# ============ JD must contain ============
JD_MUST_CONTAIN = [
    "real estate", "commercial real estate", " cre ",
    "repe", "reit", "reits",
    "alternative investment", "alternative investments", "alternatives",
    "private markets", "private equity real estate",
    "real assets", "infrastructure fund", "direct real estate",
    "property investment", "property fund", "realty",
    "aum", "institutional investor", "institutional investors",
    "asset management firm", "amc", "asset management company",
    "multifamily", "industrial real estate", "office real estate",
    "retail real estate", "hospitality real estate",
    "cmbs", "mortgage-backed", "mortgage backed",
    "cap rate", "noi ", "argus", "dcf", "underwriting",
    # Financial modeling — NEW
    "financial modeling", "financial modelling",
    "three statement model", "3-statement model", "lbo model",
    "dcf model", "merger model", "acquisition model",
    "waterfall model", "waterfall analysis",
    "valuation model", "valuation analysis",
    "scenario analysis", "sensitivity analysis",
    "operating model", "build a model", "building models",
    "complex models", "financial models",
]


# ============ Dedup ============
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


# ============ Filter helpers ============
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
    c = (company_name or "").lower()
    return any(tc in c for tc in TARGET_COMPANIES)


def passes_location_filter(job):
    loc = (job.get("location") or "").lower()
    if any(h in loc for h in INDIA_HINTS):
        return True
    is_remote = "remote" in loc
    is_hybrid = "hybrid" in loc
    return is_remote and not is_hybrid


def jd_mentions_re(job, client):
    """Generic JD checker. Each scraper provides 'jd_url' or 'jd_text'."""
    text = job.get("jd_text", "")
    if not text and job.get("jd_url"):
        try:
            r = client.get(job["jd_url"], headers=HEADERS, timeout=20)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                desc = soup.select_one(
                    "div.show-more-less-html__markup, "
                    "div.description__text, "
                    "div[class*='description'], "
                    "section[class*='description']"
                )
                text = desc.get_text(" ", strip=True).lower() if desc else \
                       soup.get_text(" ", strip=True).lower()
        except Exception:
            return False
    if not text:
        return False
    return any(term in text.lower() for term in JD_MUST_CONTAIN)


# ============ Telegram ============
def send_telegram(job, reason):
    star = "⭐ " if is_target_company(job["company"]) else ""
    source = job.get("source", "")
    src_tag = f" `[{source}]`" if source else ""
    text = (
        f"🎯 {star}*{job['title']}*{src_tag}\n"
        f"🏢 {job['company']}\n"
        f"📍 {job['location']}\n"
        f"⏱️ {job.get('posted', 'recent')}\n"
        f"_{reason}_\n\n"
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
