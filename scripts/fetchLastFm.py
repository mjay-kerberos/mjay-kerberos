#!/usr/bin/env python3
"""
Last.fm Stats Collector
Fetches listening statistics from Last.fm API
"""

import os
import json
import requests
from datetime import datetime
from typing import List

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"


class LastFMClient:
    """Client for interacting with Last.fm API."""

    def __init__(self, api_key: str, username: str):
        self.api_key = api_key
        self.username = username

    def _make_request(self, method: str, **params) -> dict:
        """Make a request to the Last.fm API."""
        params.update({
            "method": method,
            "user": self.username,
            "api_key": self.api_key,
            "format": "json"
        })

        resp = requests.get(LASTFM_API_URL, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_user_info(self) -> dict:
        """Get user profile information including total scrobbles."""
        data = self._make_request("user.getinfo")
        user = data["user"]

        return {
            "username": user["name"],
            "real_name": user.get("realname", ""),
            "country": user.get("country", ""),
            "total_scrobbles": int(user["playcount"]),
            "registered": int(user["registered"].get("unixtime", 0)),
            "profile_url": user["url"],
        }

    def get_top_artists(self, period: str = "overall", limit: int = 10) -> List[dict]:
        data = self._make_request("user.gettopartists", period=period, limit=limit)
        artists = []
        for artist in data.get("topartists", {}).get("artist", []):
            artists.append({
                "name": artist["name"],
                "playcount": int(artist["playcount"]),
                "url": artist["url"],
                "rank": int(artist["@attr"]["rank"]),
            })
        return artists

    def get_top_tracks(self, period: str = "overall", limit: int = 10) -> List[dict]:
        data = self._make_request("user.gettoptracks", period=period, limit=limit)
        tracks = []
        for track in data.get("toptracks", {}).get("track", []):
            tracks.append({
                "name": track["name"],
                "artist": track["artist"]["name"],
                "playcount": int(track["playcount"]),
                "url": track["url"],
                "rank": int(track["@attr"]["rank"]),
            })
        return tracks

    def get_top_albums(self, period: str = "overall", limit: int = 10) -> List[dict]:
        data = self._make_request("user.gettopalbums", period=period, limit=limit)
        albums = []
        for album in data.get("topalbums", {}).get("album", []):
            albums.append({
                "name": album["name"],
                "artist": album["artist"]["name"],
                "playcount": int(album["playcount"]),
                "url": album["url"],
                "rank": int(album["@attr"]["rank"]),
            })
        return albums

    def get_weekly_chart(self) -> dict:
        data = self._make_request("user.getweeklytrackchart")
        tracks = data.get("weeklytrackchart", {}).get("track", [])
        total_plays = sum(int(t.get("playcount", 0)) for t in tracks)
        return {
            "total_tracks_this_week": len(tracks),
            "total_plays_this_week": total_plays,
        }

    def estimate_listening_time(self, avg_track_duration_minutes: float = 3.5) -> dict:
        """
        Lifetime listening time estimate based on total scrobbles.
        """
        user_info = self.get_user_info()
        total_scrobbles = user_info["total_scrobbles"]

        total_minutes = total_scrobbles * avg_track_duration_minutes
        total_hours = total_minutes / 60
        total_days = total_hours / 24

        return {
            "total_scrobbles": total_scrobbles,
            "estimated_minutes": round(total_minutes),
            "estimated_hours": round(total_hours, 1),
            "estimated_days": round(total_days, 1),
            "avg_track_duration_assumed": avg_track_duration_minutes,
        }

    def estimate_period_listening_time(
        self,
        period: str,
        avg_track_duration_minutes: float = 3.5,
        limit: int = 1000,
    ) -> dict:
        """
        Estimate listening time for a given Last.fm period using top tracks.

        period values:
          - "7day"   -> last 7 days
          - "1month" -> last month
          - "12month"-> last 12 months

        This sums playcount for the top tracks in that period and multiplies
        by an average track length.
        """
        tracks = self.get_top_tracks(period=period, limit=limit)
        total_scrobbles = sum(t["playcount"] for t in tracks)

        total_minutes = total_scrobbles * avg_track_duration_minutes
        total_hours = total_minutes / 60

        return {
            "period": period,
            "total_scrobbles": total_scrobbles,
            "estimated_minutes": round(total_minutes),
            "estimated_hours": round(total_hours, 1),
            "avg_track_duration_assumed": avg_track_duration_minutes,
        }


def get_all_lastfm_stats(api_key: str, username: str) -> dict:
    """
    Fetch all Last.fm statistics for a user.
    Used by pushToGrafana.py
    """
    client = LastFMClient(api_key, username)

    print(f"Fetching Last.fm stats for {username}...")

    user_info = client.get_user_info()

    # Top lists
    top_artists_overall = client.get_top_artists(period="overall", limit=10)
    top_tracks_overall = client.get_top_tracks(period="overall", limit=10)
    top_tracks_week = client.get_top_tracks(period="7day", limit=5)
    top_albums_overall = client.get_top_albums(period="overall", limit=5)

    # Weekly stats
    weekly_stats = client.get_weekly_chart()

    # Lifetime listening time
    listening_time = client.estimate_listening_time()

    listening_time_7day = client.estimate_period_listening_time("7day")
    listening_time_1month = client.estimate_period_listening_time("1month")
    listening_time_12month = client.estimate_period_listening_time("12month")

    return {
        "user": user_info,
        "listening_time": listening_time,
        "listening_time_periods": {
            "7day": listening_time_7day,
            "1month": listening_time_1month,
            "12month": listening_time_12month,
        },
        "weekly_stats": weekly_stats,
        "top_artists": {
            "overall": top_artists_overall,
        },
        "top_tracks": {
            "overall": top_tracks_overall,
            "week": top_tracks_week,
        },
        "top_albums": {
            "overall": top_albums_overall,
        },
        "fetched_at": datetime.now().isoformat(),
    }


def get_lastfm_stats(api_key: str, username: str) -> dict:
    """Small wrapper kept for compat with imports in pushToGrafana.py."""
    return get_all_lastfm_stats(api_key, username)


def get_lastfm_estimated_minutes(
    api_key: str,
    username: str,
    avg_track_duration_minutes: float = 3.5,
) -> float:
    client = LastFMClient(api_key, username)
    listening_time = client.estimate_listening_time(avg_track_duration_minutes)
    return listening_time["estimated_minutes"]


def main():
    api_key = os.environ.get("LASTFM_API_KEY")
    username = os.environ.get("LASTFM_USERNAME")

    if not api_key:
        raise ValueError("LASTFM_API_KEY environment variable is required")
    if not username:
        raise ValueError("LASTFM_USERNAME environment variable is required")

    stats = get_all_lastfm_stats(api_key, username)

    print(f"\n=== Last.fm Stats for {stats['user']['username']} ===")
    print(f"Total Scrobbles: {stats['user']['total_scrobbles']:,}")
    print(
        f"Lifetime Estimated Listening Time: "
        f"{stats['listening_time']['estimated_hours']:,} hours "
        f"({stats['listening_time']['estimated_days']} days)"
    )


    lt7 = stats["listening_time_periods"]["7day"]
    lt1m = stats["listening_time_periods"]["1month"]
    lt12m = stats["listening_time_periods"]["12month"]

    print(
        f"\nLast 7 days: ~{lt7['estimated_minutes']} minutes "
        f"({lt7['estimated_hours']} hours)"
    )
    print(
        f"Last 1 month: ~{lt1m['estimated_minutes']} minutes "
        f"({lt1m['estimated_hours']} hours)"
    )
    print(
        f"Last 12 months: ~{lt12m['estimated_minutes']} minutes "
        f"({lt12m['estimated_hours']} hours)"
    )

    return stats


if __name__ == "__main__":
    stats = main()
    print("\n=== JSON Output ===")
    print(json.dumps(stats, indent=2, default=str))
