from common import HEADERS

# Each entry: (greenhouse_board_token, friendly_company_name)
# These are real, verified Greenhouse boards as of writing — but companies move
# their boards sometimes. If a company stops appearing, check
# https://boards.greenhouse.io/{token} in a browser.
GREENHOUSE_COMPANIES = [
    ("greystar", "Greystar"),
    ("cortland", "Cortland"),
    ("cadre", "Cadre"),
    ("fundrise", "Fundrise"),
    ("opendoor", "Opendoor"),
    ("compass", "Compass"),
    ("vts", "VTS"),
    ("juniper-square", "Juniper Square"),
    ("blend", "Blend"),
    ("morningstar", "Morningstar"),
    ("bain-capital-credit", "Bain Capital Credit"),
    ("ares-management", "Ares Management"),
    ("ke-holdings", "KE Holdings"),
    ("knotel", "Knotel"),
    ("industrious", "Industrious"),
    ("convene", "Convene"),
]


def fetch_all(client):
    all_jobs = []
    for token, friendly in GREENHOUSE_COMPANIES:
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        try:
            r = client.get(url, headers=HEADERS)
            if r.status_code != 200:
                continue
            data = r.json()
            for job in data.get("jobs", []):
                jid = str(job.get("id"))
                title = job.get("title", "")
                loc = (job.get("location") or {}).get("name", "?")
                jd_text = (job.get("content") or "").replace("&lt;", "<")
                # Strip HTML tags crudely for keyword search
                import re
                jd_text = re.sub(r"<[^>]+>", " ", jd_text).lower()
                all_jobs.append({
                    "id": f"gh-{token}-{jid}",
                    "title": title,
                    "company": friendly,
                    "location": loc,
                    "posted": job.get("updated_at", "recent")[:10],
                    "url": job.get("absolute_url", ""),
                    "jd_text": jd_text,
                    "source": "Greenhouse",
                })
        except Exception as e:
            print(f"    [gh:{token}] error: {e}", flush=True)
    return all_jobs
