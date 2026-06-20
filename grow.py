#!/usr/bin/env python3
"""LeafLore content automation.

Each run, this moves a small number of plants from the backlog into the live
database and rebuilds the site. Running it on a schedule gives the site a
steady stream of fresh pages with no manual work, which search engines reward.

Usage:
    python grow.py            # publish the default batch (2 plants) + rebuild
    python grow.py --count 1  # publish 1 plant
    python grow.py --status   # show how much inventory is left
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOG = DATA / "grow.log"

PLANTS = DATA / "plants.json"
BACKLOG = DATA / "backlog.json"


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def status():
    live = load(PLANTS)
    backlog = load(BACKLOG)
    print(f"Live plants:   {len(live)}")
    print(f"In backlog:    {len(backlog)}")
    if backlog:
        print("Next up:       " + ", ".join(p["common_name"] for p in backlog[:5]))
    else:
        print("Backlog empty - add more plants to data/backlog.json to keep growing.")


def publish(count):
    live = load(PLANTS)
    backlog = load(BACKLOG)

    if not backlog:
        log("Backlog empty - nothing new to publish. Rebuilding existing site only.")
        rebuild()
        return

    live_slugs = {p["slug"] for p in live}
    promoted = []
    while backlog and len(promoted) < count:
        item = backlog.pop(0)
        if item["slug"] in live_slugs:
            continue  # skip duplicates already published
        live.append(item)
        live_slugs.add(item["slug"])
        promoted.append(item["common_name"])

    save(PLANTS, live)
    save(BACKLOG, backlog)

    if promoted:
        log(f"Published {len(promoted)} new guide(s): {', '.join(promoted)}. "
            f"Live total: {len(live)}. Backlog remaining: {len(backlog)}.")
    rebuild()


def rebuild():
    result = subprocess.run([sys.executable, str(ROOT / "build.py")],
                            capture_output=True, text=True)
    if result.returncode != 0:
        log(f"BUILD FAILED: {result.stderr.strip()}")
        sys.exit(1)
    log("Rebuilt site: " + result.stdout.strip().replace("\n", " | "))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=2, help="plants to publish this run")
    ap.add_argument("--status", action="store_true", help="show inventory and exit")
    args = ap.parse_args()

    if args.status:
        status()
        return
    publish(args.count)


if __name__ == "__main__":
    main()
