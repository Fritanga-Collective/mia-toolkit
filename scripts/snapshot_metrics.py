#!/usr/bin/env python3
"""Append today's GitHub download/traffic snapshot to website/data/metrics.json.

Reads aggregates GitHub already publishes (release asset download counts,
14-day repo traffic) — no new tracking of anyone. Run daily by metrics.yml.
Requires: gh CLI authenticated (GH_TOKEN in CI).
"""
import datetime
import json
import os
import subprocess

REPO = os.environ.get("GITHUB_REPOSITORY", "Fritanga-Collective/mia-toolkit")
OUT = os.path.join(os.path.dirname(__file__), "..", "website", "data",
                   "metrics.json")


def gh(path, paginate=False):
    cmd = ["gh", "api", path]
    if paginate:
        # --slurp wraps each page in an outer array; flatten below.
        cmd += ["--paginate", "--slurp"]
    out = json.loads(subprocess.run(cmd, capture_output=True, text=True,
                                    check=True).stdout)
    if paginate:
        return [item for page in out for item in page]
    return out


def main():
    today = datetime.date.today().isoformat()
    releases = gh(f"repos/{REPO}/releases?per_page=100", paginate=True)
    rel = [{"tag": r["tag_name"],
            "assets": [{"name": a["name"], "count": a["download_count"]}
                       for a in r["assets"]]}
           for r in releases]
    total = sum(a["count"] for r in rel for a in r["assets"])
    try:
        views = gh(f"repos/{REPO}/traffic/views")
        referrers = gh(f"repos/{REPO}/traffic/popular/referrers")
    except subprocess.CalledProcessError:
        views, referrers = {"count": 0, "uniques": 0}, []

    data = {"snapshots": [], "releases": [], "referrers": [], "updated": ""}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            data = json.load(f)

    snap = {"date": today, "total": total,
            "views14": views.get("count", 0),
            "uniques14": views.get("uniques", 0)}
    data["snapshots"] = [s for s in data["snapshots"] if s["date"] != today]
    data["snapshots"].append(snap)
    data["snapshots"].sort(key=lambda s: s["date"])
    data["releases"] = rel                      # latest cumulative state
    data["referrers"] = [{"referrer": r["referrer"], "count": r["count"]}
                         for r in referrers[:8]]
    data["updated"] = today

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"snapshot {today}: total={total}, views14={snap['views14']}")


if __name__ == "__main__":
    main()
