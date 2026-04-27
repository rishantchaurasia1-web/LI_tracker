import os
import time
import random
import httpx
from scrapers import linkedin_guest, naukri, greenhouse, lever, workday
from common import (
    load_seen, save_seen, send_telegram,
    title_has_excludes, title_has_includes, title_has_path_b_hint,
    is_target_company, passes_location_filter, jd_mentions_re,
)

MAX_JD_FETCHES_PER_RUN = 20
DELAY_BETWEEN_SOURCES = 4

def process_jobs(jobs, seen, jd_budget, client):
    """Common filter pipeline used by every source."""
    matched = alerted = failed = 0
    jd_used = 0
    for job in jobs:
        if job["id"] in seen:
            continue
        if title_has_excludes(job):
            continue
        if not passes_location_filter(job):
            continue

        is_target = is_target_company(job["company"])
        title_match = title_has_includes(job)
        reason = None

        if title_match:
            reason = "title match"
        elif is_target:
            if jd_used < jd_budget:
                jd_used += 1
                if jd_mentions_re(job, client):
                    reason = "target co. + JD match"
        elif title_has_path_b_hint(job):
            if jd_used < jd_budget:
                jd_used += 1
                if jd_mentions_re(job, client):
                    reason = "JD match"

        if reason is None:
            continue

        matched += 1
        if send_telegram(job, reason):
            seen[job["id"]] = int(time.time())
            alerted += 1
            print(f"  ✅ [{reason}] {job['title']} @ {job['company']} — {job['location']}", flush=True)
        else:
            failed += 1
        time.sleep(1)
    return matched, alerted, failed, jd_used


def run_once():
    seen = load_seen()
    print(f"Loaded {len(seen)} previously-seen job ids", flush=True)

    total_scanned = total_matched = total_alerted = total_failed = 0
    jd_budget = MAX_JD_FETCHES_PER_RUN

    sources = [
        ("LinkedIn (guest)", linkedin_guest.fetch_all),
        ("Naukri",           naukri.fetch_all),
        ("Greenhouse",       greenhouse.fetch_all),
        ("Lever",            lever.fetch_all),
        ("Workday",          workday.fetch_all),
    ]
    random.shuffle(sources)

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for name, fetch_fn in sources:
            print(f"\n=== {name} ===", flush=True)
            try:
                jobs = fetch_fn(client)
            except Exception as e:
                print(f"  {name} crashed: {e}", flush=True)
                jobs = []
            print(f"  fetched {len(jobs)} jobs", flush=True)
            total_scanned += len(jobs)
            m, a, f, used = process_jobs(jobs, seen, jd_budget, client)
            jd_budget -= used
            total_matched += m
            total_alerted += a
            total_failed += f
            time.sleep(DELAY_BETWEEN_SOURCES)

    save_seen(seen)
    print(f"\nTOTAL — scanned {total_scanned}, matched {total_matched}, "
          f"alerted {total_alerted}, failed {total_failed}, "
          f"JD budget remaining {jd_budget}", flush=True)


if __name__ == "__main__":
    run_once()
