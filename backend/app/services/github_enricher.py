import httpx
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from app.config import settings

logger = logging.getLogger(__name__)

def extract_github_username(links: List[str]) -> Optional[str]:
    """
    Scans a list of links for a GitHub profile and extracts the username.
    """
    for link in links:
        if "github.com" in link.lower():
            url = link.strip()
            # Standardize URL for urlparse
            if not url.lower().startswith("http"):
                url = "https://" + url
            try:
                parsed = urlparse(url)
                path = parsed.path.strip("/")
                parts = path.split("/")
                if len(parts) > 0 and parts[0]:
                    # Ignore standard non-username paths if any
                    username = parts[0]
                    if username.lower() not in ("sponsors", "features", "enterprise", "pricing"):
                        return username
            except Exception as e:
                logger.warning(f"Failed to parse potential GitHub link '{link}': {str(e)}")
                continue
    return None

async def enrich_profile_with_github(github_username: str) -> Dict[str, Any]:
    """
    Queries the GitHub API to fetch repo counts, primary languages, and stars.
    Returns a default safe structure on failure to prevent blocking the intake pipeline.
    """
    enrichment_data = {
        "username": github_username,
        "total_stars": 0,
        "languages": {},
        "top_repositories": []
    }

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Resume-Generator-Backend"
    }
    if settings.GITHUB_TOKEN and not settings.GITHUB_TOKEN.startswith("mock-"):
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            url = f"https://api.github.com/users/{github_username}/repos"
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.warning(f"GitHub user '{github_username}' not found.")
                return enrichment_data
            elif response.status_code in (403, 429):
                logger.warning(f"GitHub API rate limit hit or forbidden ({response.status_code}). Skipping enrichment.")
                return enrichment_data
            elif response.status_code != 200:
                logger.warning(f"GitHub API returned unexpected status: {response.status_code}.")
                return enrichment_data

            repos = response.json()
            if not isinstance(repos, list):
                logger.warning("GitHub API returned invalid structure (expected list of repos).")
                return enrichment_data

            total_stars = 0
            languages = {}
            valid_repos = []

            for repo in repos:
                # Exclude forks to measure only original candidate work
                if repo.get("fork"):
                    continue

                stars = repo.get("stargazers_count", 0)
                total_stars += stars

                lang = repo.get("language")
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1

                valid_repos.append({
                    "name": repo.get("name"),
                    "description": repo.get("description"),
                    "language": lang,
                    "stars": stars,
                    "url": repo.get("html_url")
                })

            # Sort repositories by stars descending and take top 5
            valid_repos.sort(key=lambda r: r["stars"], reverse=True)
            top_repos = valid_repos[:5]

            enrichment_data["total_stars"] = total_stars
            enrichment_data["languages"] = languages
            enrichment_data["top_repositories"] = top_repos

            logger.info(f"Successfully enriched profile from GitHub for user '{github_username}'")
            return enrichment_data

        except httpx.RequestError as e:
            logger.error(f"Network request to GitHub failed: {str(e)}. Gracefully degrading.")
            return enrichment_data
        except Exception as e:
            logger.error(f"Unexpected error in GitHub enrichment: {str(e)}. Gracefully degrading.")
            return enrichment_data
