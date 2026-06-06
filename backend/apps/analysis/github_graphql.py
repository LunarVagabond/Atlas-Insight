import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def gql(query: str, variables: dict, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token or settings.GITHUB_TOKEN}"}
    resp = requests.post(
        GITHUB_GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GitHub GraphQL errors: {data['errors']}")
    return data["data"]


REPO_META_QUERY = """
query RepoMeta($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    url
    description
    stargazerCount
    forkCount
    isArchived
    isFork
    isPrivate
    homepageUrl
    hasWikiEnabled
    hasDiscussionsEnabled
    openIssues: issues(states: OPEN) { totalCount }
    openPullRequests: pullRequests(states: OPEN) { totalCount }
    watchers { totalCount }
    diskUsage
    createdAt
    pushedAt
    primaryLanguage { name }
    defaultBranchRef { name }
    repositoryTopics(first: 10) {
      nodes { topic { name } }
    }
    licenseInfo { spdxId name }
    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
      totalSize
      edges { size node { name } }
    }
    releases(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { tagName publishedAt isPrerelease isDraft }
    }
  }
  rateLimit { remaining cost }
}
"""


def _build_releases_meta(nodes: list[dict]) -> dict | None:
    if not nodes:
        return None
    stable = [r for r in nodes if not r.get("isPrerelease") and not r.get("isDraft")]
    prereleases = [r for r in nodes if r.get("isPrerelease") and not r.get("isDraft")]

    def _rel(r: dict) -> dict:
        return {"name": r.get("tagName", ""), "date": r.get("publishedAt", "")}

    return {
        "stable_count": len(stable),
        "prerelease_count": len(prereleases),
        "total_count": len(stable) + len(prereleases),
        "latest_stable": _rel(stable[0]) if stable else None,
        "latest_prerelease": _rel(prereleases[0]) if prereleases else None,
    }


def fetch_repo_meta_graphql(owner: str, name: str, token: str | None = None) -> dict:
    """Fetch repository metadata via GraphQL. Returns a dict matching the fetch_github_meta() shape
    (minus 'contributors' and 'contribution_data', which remain REST calls)."""
    data = gql(REPO_META_QUERY, {"owner": owner, "name": name}, token=token)
    repo = data["repository"]

    topics = [node["topic"]["name"] for node in repo.get("repositoryTopics", {}).get("nodes", [])]
    license_info = repo.get("licenseInfo") or {}

    lang_edges = repo.get("languages", {}).get("edges", [])
    total_size = repo.get("languages", {}).get("totalSize") or 1
    github_languages = sorted(
        [
            {
                "name": edge["node"]["name"],
                "bytes": edge["size"],
                "pct": round(edge["size"] / total_size * 100, 1),
            }
            for edge in lang_edges
        ],
        key=lambda x: -x["bytes"],
    )

    releases_meta = _build_releases_meta(repo.get("releases", {}).get("nodes", []))
    default_branch = (repo.get("defaultBranchRef") or {}).get("name") or "main"

    logger.debug(
        "GraphQL fetch for %s/%s cost %s point(s), %s remaining",
        owner, name,
        data.get("rateLimit", {}).get("cost"),
        data.get("rateLimit", {}).get("remaining"),
    )

    return {
        "html_url": repo.get("url"),
        "stars": repo["stargazerCount"],
        "forks": repo["forkCount"],
        "open_issues": repo.get("openIssues", {}).get("totalCount", 0),
        "open_prs": repo.get("openPullRequests", {}).get("totalCount"),
        "watchers": repo.get("watchers", {}).get("totalCount", 0),
        "primary_language": (repo.get("primaryLanguage") or {}).get("name"),
        "topics": topics,
        "license_spdx": license_info.get("spdxId"),
        "license_name": license_info.get("name"),
        "github_description": repo.get("description"),
        "size_kb": repo.get("diskUsage", 0),
        "default_branch": default_branch,
        "has_wiki": repo.get("hasWikiEnabled", False),
        "has_discussions": repo.get("hasDiscussionsEnabled", False),
        "archived": repo["isArchived"],
        "is_fork": repo["isFork"],
        "is_private": repo["isPrivate"],
        "created_at": repo.get("createdAt"),
        "pushed_at": repo.get("pushedAt"),
        "homepage": repo.get("homepageUrl") or None,
        "releases_meta": releases_meta,
        "github_languages": github_languages,
    }
