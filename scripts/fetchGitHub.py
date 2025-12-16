#!/usr/bin/env python3
"""
GitHub Stats Collector
Fetches contribution data using GitHub GraphQL API
"""

import os
import json
import requests
from datetime import datetime

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

def get_github_stats(token: str, username: str = None) -> dict:
    """
    Fetch GitHub contribution statistics using GraphQL API.

    Args:
        token: GitHub Personal Access Token
        username: GitHub username (optional, fetches viewer if not provided)

    Returns:
        Dictionary containing GitHub stats
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # GraphQL query for contribution data
    query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        login
        name
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalRepositoryContributions
          restrictedContributionsCount
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
          totalCount
        }
        repositoriesContributedTo(first: 100, contributionTypes: [COMMIT, PULL_REQUEST, ISSUE]) {
          totalCount
        }
        organizations(first: 100) {
          totalCount
        }
      }
    }
    """

    # If no username provided, get viewer's username first
    if not username:
        viewer_query = "query { viewer { login } }"
        response = requests.post(
            GITHUB_GRAPHQL_URL,
            headers=headers,
            json={"query": viewer_query}
        )
        response.raise_for_status()
        username = response.json()["data"]["viewer"]["login"]

    # Get current year date range
    current_year = datetime.now().year
    from_date = f"{current_year}-01-01T00:00:00Z"
    to_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    variables = {
        "username": username,
        "from": from_date,
        "to": to_date
    }

    response = requests.post(
        GITHUB_GRAPHQL_URL,
        headers=headers,
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")

    user_data = data["data"]["user"]
    contributions = user_data["contributionsCollection"]
    commits_this_month = calculate_monthly_commits(
    contributions["contributionCalendar"]
)

    # Calculate total commits including private
    total_commits = (
        contributions["totalCommitContributions"] +
        contributions["restrictedContributionsCount"]
    )

    stats = {
        "username": user_data["login"],
        "name": user_data.get("name", user_data["login"]),
        "total_commits_this_year": total_commits,
        "public_commits": contributions["totalCommitContributions"],
        "private_commits": contributions["restrictedContributionsCount"],
        "commits_this_month": commits_this_month,
        "total_prs": contributions["totalPullRequestContributions"],
        "total_issues": contributions["totalIssueContributions"],
        "total_contributions": contributions["contributionCalendar"]["totalContributions"],
        "repos_owned": user_data["repositories"]["totalCount"],
        "repos_contributed_to": user_data["repositoriesContributedTo"]["totalCount"],
        "organizations": user_data["organizations"]["totalCount"],
        "year": current_year,
        "fetched_at": datetime.now().isoformat()
    }

    return stats
    
def get_all_time_stats(token: str, username: str = None) -> dict:
    """
    Fetch all-time GitHub statistics.

    Args:
        token: GitHub Personal Access Token
        username: GitHub username

    Returns:
        Dictionary containing all-time stats
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Get viewer username if not provided
    if not username:
        viewer_query = "query { viewer { login } }"
        response = requests.post(
            GITHUB_GRAPHQL_URL,
            headers=headers,
            json={"query": viewer_query}
        )
        response.raise_for_status()
        username = response.json()["data"]["viewer"]["login"]

    # Query for all-time repository stats
    query = """
    query($username: String!) {
      user(login: $username) {
        login
        createdAt
        repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
          totalCount
          nodes {
            name
            isPrivate
            isFork
            stargazerCount
            forkCount
          }
        }
        repositoriesContributedTo(first: 100, contributionTypes: [COMMIT, PULL_REQUEST, ISSUE]) {
          totalCount
        }
        pullRequests(first: 1) {
          totalCount
        }
        issues(first: 1) {
          totalCount
        }
      }
    }
    """

    response = requests.post(
        GITHUB_GRAPHQL_URL,
        headers=headers,
        json={"query": query, "variables": {"username": username}}
    )
    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")

    user_data = data["data"]["user"]
    repos = user_data["repositories"]["nodes"]

    # Calculate stats from repos
    total_stars = sum(repo["stargazerCount"] for repo in repos)
    total_forks = sum(repo["forkCount"] for repo in repos)
    private_repos = sum(1 for repo in repos if repo["isPrivate"])
    public_repos = sum(1 for repo in repos if not repo["isPrivate"])

    stats = {
        "username": user_data["login"],
        "account_created": user_data["createdAt"],
        "total_repos": user_data["repositories"]["totalCount"],
        "public_repos": public_repos,
        "private_repos": private_repos,
        "repos_contributed_to": user_data["repositoriesContributedTo"]["totalCount"],
        "total_prs_all_time": user_data["pullRequests"]["totalCount"],
        "total_issues_all_time": user_data["issues"]["totalCount"],
        "total_stars_received": total_stars,
        "total_forks_received": total_forks,
        "fetched_at": datetime.now().isoformat()
    }

    return stats

def calculate_monthly_commits(contribution_calendar: dict) -> int:
    """Return number of commits made in the current month."""
    now = datetime.utcnow()
    current_year = now.year
    current_month = now.month

    monthly_total = 0

    for week in contribution_calendar.get("weeks", []):
        for day in week.get("contributionDays", []):
            date = datetime.fromisoformat(day["date"].replace("Z", ""))
            if date.year == current_year and date.month == current_month:
                monthly_total += day["contributionCount"]

    return monthly_total
    
def main():
    """Main function to fetch and display GitHub stats."""
    token = os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("GITHUB_USERNAME")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    print("Fetching GitHub stats...")

    # Get current year stats
    year_stats = get_github_stats(token, username)
    print(f"\n=== {year_stats['year']} Stats for {year_stats['username']} ===")
    print(f"Total Commits: {year_stats['total_commits_this_year']}")
    print(f"  - Public: {year_stats['public_commits']}")
    print(f"  - Private: {year_stats['private_commits']}")
    print(f"Total Contributions: {year_stats['total_contributions']}")
    print(f"Pull Requests: {year_stats['total_prs']}")
    print(f"Issues: {year_stats['total_issues']}")
    print(f"Repos Owned: {year_stats['repos_owned']}")
    print(f"Repos Contributed To: {year_stats['repos_contributed_to']}")
    print(f"Organizations: {year_stats['organizations']}")

    # Get all-time stats
    all_time_stats = get_all_time_stats(token, username)
    print(f"\n=== All-Time Stats ===")
    print(f"Total Repos: {all_time_stats['total_repos']}")
    print(f"  - Public: {all_time_stats['public_repos']}")
    print(f"  - Private: {all_time_stats['private_repos']}")
    print(f"Stars Received: {all_time_stats['total_stars_received']}")
    print(f"Forks Received: {all_time_stats['total_forks_received']}")
    print(f"All-Time PRs: {all_time_stats['total_prs_all_time']}")
    print(f"All-Time Issues: {all_time_stats['total_issues_all_time']}")

    # Return combined stats for use by other scripts
    return {
        "year_stats": year_stats,
        "all_time_stats": all_time_stats
    }


if __name__ == "__main__":
    stats = main()
    print(f"\n=== JSON Output ===")
    print(json.dumps(stats, indent=2))
