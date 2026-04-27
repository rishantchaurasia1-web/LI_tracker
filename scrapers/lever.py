from common import HEADERS

# Each entry: (lever_company_id, friendly_name)
LEVER_COMPANIES = [
    ("matterport", "Matterport"),
    ("hippopotamus", "Hippo Insurance"),
    ("brex", "Brex"),
    ("addepar", "Addepar"),
    ("ramp", "Ramp"),
    ("ondeck", "OnDeck"),
    # Add more as you discover them via lever.co/{company}
]


def fetch_all(client):
    all_jobs = []
    for cid, friendly in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{cid}?mode=json"
        try:
            r = client.get(url, headers=HEADERS)
            if r.status_code != 200:
                continue
            for job in r.json():
                jid = job.get("id", "")
                title = job.get("text", "")
                loc = ((job.get("categories") or {}).get("location")) or "?"
                jd_text = (job.get("descriptionPlain") or "").lower()
                # also include lists
                for lst in job.get("lists", []):
                    jd_text += " " + (lst.get("content") or "").lower()
                all_jobs.append({
                    "id": f"lever-{cid}-{jid}",
                    "title": title,
                    "company": friendly,
                    "location": loc,
                    "posted": "recent",
                    "url": job.get("hostedUrl", ""),
                    "jd_text": jd_text,
                    "source": "Lever",
                })
        except Exception as e:
            print(f"    [lever:{cid}] error: {e}", flush=True)
    return all_jobs
