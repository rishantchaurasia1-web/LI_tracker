import os
import time
import random
from linkedin_api import Linkedin
from common import (
    load_seen, save_seen, send_telegram,
    INCLUDE_KEYWORDS, EXCLUDE_KEYWORDS, JD_MUST_CONTAIN,
    INDIA_HINTS, is_target_company,
)

LI_EMAIL = os.environ["LI_EMAIL"]
LI_PASSWORD = os.environ["LI_PASSWORD"]

# Keywords to search for in post text
POST_QUERIES = [
    "#hiring real estate analyst",
    "#hiring acquisitions analyst",
    "#hiring real estate associate",
    "#hiring financial modeling",
    "#hiring valuation analyst",
    "#realestate hiring india",
    "#hiringalert real estate",
    "real estate analyst hiring",
    "financial modeling hiring",
]

# Tighter content match for posts (free-form text, not job listings)
POST_MUST_CONTAIN = [
    "real estate", "acquisitions", "underwriting",
    "financial model", "financial modeling", "financial modelling",
    "valuation", "asset management", "private equity",
    "argus", "dcf", "lbo", "waterfall",
]


def post_passes_filter(post_text):
    t = post_text.lower()
    if not any(term in t for term in POST_MUST_CONTAIN):
        return False
    # Must mention India OR remote, since author location is unreliable
    if not any(h in t for h in INDIA_HINTS) and "remote" not in t:
        # Still pass if it has strong hiring signal
        if "#hiring" not in t:
            return False
    return True


def send_post_alert(post, query):
    text = post.get("text", "")[:600]  # Telegram limit awareness
    author = post.get("author_name", "Unknown")
    company = post.get("author_company", "")
    url = post.get("url", "")
    msg = (
        f"📢 *LinkedIn HR Post* `[{query}]`\n"
        f"👤 {author}"
        + (f" ({company})" if company else "")
        + f"\n\n{text}\n\n"
        f"[View post →]({url})"
    )
    return send_telegram(
        {"title": author, "company": company or "?", "location": "(post)",
         "url": url, "posted": "recent", "source": "LI-Post"},
        f"post: {query}",
    )


def run_once():
    seen = load_seen()
    print(f"Loaded {len(seen)} previously-seen ids", flush=True)

    # Random pre-delay so we don't run at exactly the same minute every time
    pre_delay = random.randint(0, 600)
    print(f"Pre-delay: {pre_delay}s", flush=True)
    time.sleep(pre_delay)

    print("Logging in to LinkedIn...", flush=True)
    api = Linkedin(LI_EMAIL, LI_PASSWORD)

    queries = list(POST_QUERIES)
    random.shuffle(queries)

    matched = alerted = 0
    for query in queries:
        print(f"\n--- searching: {query} ---", flush=True)
        try:
            results = api.search(params={"keywords": query, "filters": "List(resultType->CONTENT)"})
        except Exception as e:
            print(f"  search failed: {e}", flush=True)
            continue

        for item in (results or [])[:30]:
            # Structure varies; we extract defensively
            urn = item.get("trackingUrn") or item.get("urn") or item.get("entityUrn") or ""
            post_id = urn.split(":")[-1] if urn else ""
            if not post_id or f"lipost-{post_id}" in seen:
                continue

            # Try to get post text
            post_text = ""
            for k in ("summary", "primarySubtitle", "snippet", "headline"):
                v = item.get(k)
                if isinstance(v, dict):
                    v = v.get("text", "")
                if v:
                    post_text += " " + str(v)
            post_text = post_text.strip()
            if not post_text:
                continue

            if not post_passes_filter(post_text):
                continue

            # Build the post URL
            url = f"https://www.linkedin.com/feed/update/{urn}/" if urn else ""
            author = item.get("title", {}).get("text", "Unknown") if isinstance(item.get("title"), dict) else str(item.get("title", "Unknown"))

            post_obj = {
                "text": post_text,
                "author_name": author,
                "author_company": "",
                "url": url,
            }
            matched += 1
            if send_post_alert(post_obj, query):
                seen[f"lipost-{post_id}"] = int(time.time())
                alerted += 1
                print(f"  ✅ {author[:60]}", flush=True)

            time.sleep(2)

        # Variable delay between searches — don't hammer
        time.sleep(random.randint(20, 60))

    save_seen(seen)
    print(f"\nMatched {matched}, alerted {alerted}", flush=True)


if __name__ == "__main__":
    run_once()
