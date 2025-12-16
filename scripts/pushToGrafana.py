#!/usr/bin/env python3
"""
Collect stats (GitHub, Last.fm, CTF) and write them to stats.json.

This script is run by the GitHub Action from the `scripts/` directory.
"""

import os
import json
from datetime import datetime

# These imports assume the following files exist in scripts/:
# - fetch_github_stats.py (with get_github_stats, get_all_time_stats)
# - fetchLastFm.py       (with get_lastfm_stats)
# - fetchCTFstats.py     (with get_all_ctf_stats)
try:
    from fetchGitHub import get_github_stats, get_all_time_stats
except ImportError:
    get_github_stats = None
    get_all_time_stats = None

try:
    from fetchLastFm import get_lastfm_stats
except ImportError:
    get_lastfm_stats = None

try:
    from fetchCTFstats import get_all_ctf_stats
except ImportError:
    get_all_ctf_stats = None


def collect_github_stats() -> dict:
    """Collect GitHub stats using GH_PAT and GITHUB_USERNAME env vars."""
    gh_pat = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    gh_user = os.environ.get("GITHUB_USERNAME")

    if not gh_pat or not gh_user or get_github_stats is None:
        print("GitHub stats: missing GH_PAT / GITHUB_USERNAME or fetch_github_stats not available.")
        return {}

    try:
        print("=== Collecting GitHub Stats ===")
        gh_stats = get_github_stats(gh_pat, gh_user)

        # Optionally merge with all-time stats if you have that function
        if get_all_time_stats is not None:
            all_time = get_all_time_stats(gh_pat, gh_user)
            gh_stats["all_time"] = all_time

        return gh_stats
    except Exception as e:
        print(f"Error collecting GitHub stats: {e}")
        return {}


def collect_lastfm_stats() -> dict:
    """Collect Last.fm stats using LASTFM_API_KEY and LASTFM_USERNAME env vars."""
    api_key = os.environ.get("LASTFM_API_KEY")
    username = os.environ.get("LASTFM_USERNAME")

    if not api_key or not username or get_lastfm_stats is None:
        print("Last.fm stats: missing LASTFM_API_KEY / LASTFM_USERNAME or fetchLastFm not available.")
        return {}

    try:
        print("\n=== Collecting Last.fm Stats ===")
        lf_stats = get_lastfm_stats(api_key, username)
        return lf_stats
    except Exception as e:
        print(f"Error collecting Last.fm stats: {e}")
        return {}


def collect_ctf_stats() -> dict:
    """Collect CTF stats from HackTheBox, TryHackMe, CTFtime (all optional)."""
    if get_all_ctf_stats is None:
        print("CTF stats: fetchCTFstats not available.")
        return {}

    htb_token = os.environ.get("HTB_API_TOKEN")
    thm_username = os.environ.get("THM_USERNAME")
    ctftime_team_id = os.environ.get("CTFTIME_TEAM_ID")

    if not any([htb_token, thm_username, ctftime_team_id]):
        print("CTF stats: no CTF credentials configured (HTB_API_TOKEN / THM_USERNAME / CTFTIME_TEAM_ID).")
        return {}

    try:
        print("\n=== Collecting CTF Stats ===")
        ctf_stats = get_all_ctf_stats(
            htb_token=htb_token,
            thm_username=thm_username,
            ctftime_team_id=ctftime_team_id,
        )
        return ctf_stats
    except Exception as e:
        print(f"Error collecting CTF stats: {e}")
        return {}


def main():
    print("Starting stats collection...")

    stats = {
        "collected_at": datetime.utcnow().isoformat() + "Z"
    }

    # --- GitHub ---
    gh_stats = collect_github_stats()
    if gh_stats:
        stats["github"] = gh_stats

    # --- Last.fm ---
    lf_stats = collect_lastfm_stats()
    if lf_stats:
        stats["lastfm"] = lf_stats

    # --- CTF ---
    ctf_stats = collect_ctf_stats()
    if ctf_stats:
        stats["ctf"] = ctf_stats

    # Write stats.json in the current working directory (scripts/)
    output_path = "stats.json"
    with open(output_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)

    print(f"\nStats saved to {output_path}")
    print(json.dumps(stats, indent=2, default=str))

    # NOTE: we are NOT pushing to Grafana here.
    # The GitHub Action will upload stats.json as an artifact and
    # move it to the repo root & commit it.


if __name__ == "__main__":
    main()
