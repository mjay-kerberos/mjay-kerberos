#!/usr/bin/env python3
"""
CTF Stats Collector
Fetches statistics from HackTheBox, TryHackMe, and CTFtime
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Optional, List

# API Endpoints
HTB_API_URL = "https://labs.hackthebox.com/api/v4"
THM_API_URL = "https://tryhackme.com/api"
CTFTIME_API_URL = "https://ctftime.org/api/v1"


class HackTheBoxClient:
    """Client for HackTheBox API."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }

    def get_user_profile(self) -> dict:
        """Get current user's profile."""
        response = requests.get(
            f"{HTB_API_URL}/user/info",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json().get("info", {})

    def get_user_activity(self) -> dict:
        """Get user's activity stats."""
        response = requests.get(
            f"{HTB_API_URL}/user/activity",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    def get_stats(self) -> dict:
        """Get comprehensive HackTheBox stats."""
        profile = self.get_user_profile()

        return {
            "platform": "HackTheBox",
            "username": profile.get("name", ""),
            "rank": profile.get("rank", "Unranked"),
            "rank_id": profile.get("rank_id", 0),
            "points": profile.get("points", 0),
            "user_owns": profile.get("user_owns", 0),
            "root_owns": profile.get("root_owns", 0),
            "challenge_owns": profile.get("challenge_owns", 0),
            "total_owns": (
                profile.get("user_owns", 0)
                + profile.get("root_owns", 0)
                + profile.get("challenge_owns", 0)
            ),
            "ranking": profile.get("ranking", 0),
            "country_ranking": profile.get("country_ranking", 0),
            "team": profile.get("team", {}).get("name")
            if profile.get("team")
            else None,
            "fetched_at": datetime.now().isoformat(),
        }


class TryHackMeClient:
    """Client for TryHackMe API."""

    def __init__(self, username: str):
        self.username = username

    def get_public_profile(self) -> dict:
        """Get user's public profile data."""
        response = requests.get(f"{THM_API_URL}/user/rank/{self.username}")
        response.raise_for_status()
        return response.json()

    def get_badges(self) -> List[dict]:
        """Get user's badges."""
        response = requests.get(f"{THM_API_URL}/badges/get/{self.username}")
        if response.status_code == 200:
            return response.json()
        return []

    def get_stats(self) -> dict:
        """Get comprehensive TryHackMe stats."""
        try:
            profile = self.get_public_profile()
            badges = self.get_badges()

            return {
                "platform": "TryHackMe",
                "username": self.username,
                "rank": profile.get("userRank", "Unranked"),
                "points": profile.get("points", 0),
                "rooms_completed": profile.get("roomsCompleted", 0),
                "badges_count": len(badges) if isinstance(badges, list) else 0,
                "streak": profile.get("streak", 0),
                "country_rank": profile.get("countryRank", 0),
                "global_rank": profile.get("globalRank", 0),
                "fetched_at": datetime.now().isoformat(),
            }
        except requests.exceptions.HTTPError as e:
            print(f"Warning: Could not fetch TryHackMe stats: {e}")
            return {
                "platform": "TryHackMe",
                "username": self.username,
                "error": str(e),
                "fetched_at": datetime.now().isoformat(),
            }


class CTFtimeClient:
    """Client for CTFtime API."""

    def __init__(self, team_id: Optional[str] = None):
        self.team_id = team_id
        self.headers = {
            "User-Agent": "GitHub-Profile-Dashboard/1.0",
        }

    def get_team_info(self) -> dict:
        """Get team information."""
        if not self.team_id:
            return {"error": "No team ID provided"}

        response = requests.get(
            f"{CTFTIME_API_URL}/teams/{self.team_id}/",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    def get_team_results(self, limit: int = 10) -> List[dict]:
        """Get team's recent CTF results."""
        if not self.team_id:
            return []

        response = requests.get(
            f"{CTFTIME_API_URL}/results/{self.team_id}/",
            headers=self.headers,
            params={"limit": limit},
        )
        if response.status_code == 200:
            return response.json()
        return []

    def get_stats(self) -> dict:
        """Get comprehensive CTFtime stats."""
        if not self.team_id:
            return {
                "platform": "CTFtime",
                "error": "No team ID configured",
                "fetched_at": datetime.now().isoformat(),
            }

        try:
            team_info = self.get_team_info()
            results = self.get_team_results(limit=50)

            # Calculate stats from results
            total_ctfs = len(results)
            total_points = sum(r.get("points", 0) for r in results)

            return {
                "platform": "CTFtime",
                "team_id": self.team_id,
                "team_name": team_info.get("name", ""),
                "country": team_info.get("country", ""),
                "rating_place": team_info.get("rating", {}).get("rating_place", 0),
                "rating_points": team_info.get("rating", {}).get("rating_points", 0),
                "ctfs_participated": total_ctfs,
                "total_points_earned": total_points,
                "aliases": team_info.get("aliases", []),
                "fetched_at": datetime.now().isoformat(),
            }
        except requests.exceptions.HTTPError as e:
            print(f"Warning: Could not fetch CTFtime stats: {e}")
            return {
                "platform": "CTFtime",
                "team_id": self.team_id,
                "error": str(e),
                "fetched_at": datetime.now().isoformat(),
            }


def get_all_ctf_stats(
    htb_token: Optional[str] = None,
    thm_username: Optional[str] = None,
    ctftime_team_id: Optional[str] = None,
) -> dict:
    """
    Fetch CTF statistics from all configured platforms.

    Args:
        htb_token: HackTheBox API token
        thm_username: TryHackMe username
        ctftime_team_id: CTFtime team ID

    Returns:
        Dictionary containing stats from all platforms
    """
    stats = {
        "platforms": [],
        "totals": {
            "total_challenges_solved": 0,
            "total_ctfs_participated": 0,
            "total_points": 0,
        },
        "fetched_at": datetime.now().isoformat(),
    }

    # HackTheBox
    if htb_token:
        print("Fetching HackTheBox stats...")
        try:
            htb_client = HackTheBoxClient(htb_token)
            htb_stats = htb_client.get_stats()
            stats["platforms"].append(htb_stats)
            stats["totals"]["total_challenges_solved"] += htb_stats.get(
                "total_owns", 0
            )
            stats["totals"]["total_points"] += htb_stats.get("points", 0)
        except Exception as e:
            print(f"Error fetching HackTheBox stats: {e}")
            stats["platforms"].append(
                {
                    "platform": "HackTheBox",
                    "error": str(e),
                }
            )

    # TryHackMe
    if thm_username:
        print("Fetching TryHackMe stats...")
        try:
            thm_client = TryHackMeClient(thm_username)
            thm_stats = thm_client.get_stats()
            stats["platforms"].append(thm_stats)
            if "error" not in thm_stats:
                stats["totals"]["total_challenges_solved"] += thm_stats.get(
                    "rooms_completed", 0
                )
                stats["totals"]["total_points"] += thm_stats.get("points", 0)
        except Exception as e:
            print(f"Error fetching TryHackMe stats: {e}")
            stats["platforms"].append(
                {
                    "platform": "TryHackMe",
                    "error": str(e),
                }
            )

    # CTFtime
    if ctftime_team_id:
        print("Fetching CTFtime stats...")
        try:
            ctftime_client = CTFtimeClient(ctftime_team_id)
            ctftime_stats = ctftime_client.get_stats()
            stats["platforms"].append(ctftime_stats)
            if "error" not in ctftime_stats:
                stats["totals"]["total_ctfs_participated"] += ctftime_stats.get(
                    "ctfs_participated", 0
                )
                stats["totals"]["total_points"] += ctftime_stats.get(
                    "total_points_earned", 0
                )
        except Exception as e:
            print(f"Error fetching CTFtime stats: {e}")
            stats["platforms"].append(
                {
                    "platform": "CTFtime",
                    "error": str(e),
                }
            )

    return stats


# === Wrapper used by pushToGrafana.py ===
def get_ctf_stats(
    htb_token: Optional[str] = None,
    thm_username: Optional[str] = None,
    ctftime_team_id: Optional[str] = None,
) -> dict:
    """
    Thin wrapper so pushToGrafana.py can call fetchCTFstats.get_ctf_stats(...)
    """
    return get_all_ctf_stats(
        htb_token=htb_token,
        thm_username=thm_username,
        ctftime_team_id=ctftime_team_id,
    )


def main():
    """Main function to fetch and display CTF stats."""
    htb_token = os.environ.get("HTB_API_TOKEN")
    thm_username = os.environ.get("THM_USERNAME")
    ctftime_team_id = os.environ.get("CTFTIME_TEAM_ID")

    if not any([htb_token, thm_username, ctftime_team_id]):
        print("Warning: No CTF platform credentials configured.")
        print("Set at least one of: HTB_API_TOKEN, THM_USERNAME, CTFTIME_TEAM_ID")

    stats = get_all_ctf_stats(htb_token, thm_username, ctftime_team_id)

    print("\n=== CTF Stats Summary ===")
    print(f"Total Challenges Solved: {stats['totals']['total_challenges_solved']}")
    print(f"Total CTFs Participated: {stats['totals']['total_ctfs_participated']}")
    print(f"Total Points: {stats['totals']['total_points']}")

    for platform_stats in stats["platforms"]:
        platform = platform_stats.get("platform", "Unknown")
        print(f"\n=== {platform} ===")

        if "error" in platform_stats:
            print(f"  Error: {platform_stats['error']}")
            continue

        if platform == "HackTheBox":
            print(f"  Username: {platform_stats.get('username', 'N/A')}")
            print(f"  Rank: {platform_stats.get('rank', 'N/A')}")
            print(f"  Points: {platform_stats.get('points', 0)}")
            print(f"  User Owns: {platform_stats.get('user_owns', 0)}")
            print(f"  Root Owns: {platform_stats.get('root_owns', 0)}")
            print(f"  Challenge Owns: {platform_stats.get('challenge_owns', 0)}")
            print(f"  Global Ranking: #{platform_stats.get('ranking', 'N/A')}")

        elif platform == "TryHackMe":
            print(f"  Username: {platform_stats.get('username', 'N/A')}")
            print(f"  Rank: {platform_stats.get('rank', 'N/A')}")
            print(f"  Points: {platform_stats.get('points', 0)}")
            print(f"  Rooms Completed: {platform_stats.get('rooms_completed', 0)}")
            print(f"  Badges: {platform_stats.get('badges_count', 0)}")
            print(f"  Streak: {platform_stats.get('streak', 0)} days")

        elif platform == "CTFtime":
            print(f"  Team: {platform_stats.get('team_name', 'N/A')}")
            print(f"  CTFs Participated: {platform_stats.get('ctfs_participated', 0)}")
            print(f"  Rating Place: #{platform_stats.get('rating_place', 'N/A')}")
            print(f"  Rating Points: {platform_stats.get('rating_points', 0)}")

    return stats


if __name__ == "__main__":
    stats = main()
    print("\n=== JSON Output ===")
    print(json.dumps(stats, indent=2))
