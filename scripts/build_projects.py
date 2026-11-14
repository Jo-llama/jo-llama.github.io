"""Build projects.json from Jo-llama's public repos tagged with the 'portfolio' topic.

To publish a repo: add the topic "portfolio" to it on GitHub. That's all.
The card is built from the repo's About section: description -> text, other topics -> tags.
Optional portfolio.json in the repo root overrides any field:
    {"title": "...", "description": "...", "tags": ["..."], "status": "..."}
Runs in GitHub Actions at deploy time; stdlib only, no dependencies.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

OWNER = "Jo-llama"
API = "https://api.github.com"


def get(url):
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        return json.load(resp)


def load_overrides(repo):
    """Return the optional portfolio.json of a repo as a dict ({} if absent or invalid)."""
    try:
        meta = get(f"{API}/repos/{repo['full_name']}/contents/portfolio.json")
        data = json.loads(base64.b64decode(meta["content"]))
        return data if isinstance(data, dict) else {}
    except urllib.error.HTTPError as err:
        if err.code != 404:
            print(f"{repo['name']}: could not read portfolio.json ({err})", file=sys.stderr)
        return {}
    except ValueError as err:
        print(f"{repo['name']}: invalid portfolio.json, ignored ({err})", file=sys.stderr)
        return {}


def load_card(repo):
    """Build the card for one repo; None if it has no description anywhere."""
    overrides = load_overrides(repo)
    default_title = repo["name"].replace("-", " ").replace("_", " ").title()
    default_tags = [t for t in repo.get("topics", []) if t != "portfolio"]
    card = {
        "title": overrides.get("title") or default_title,
        "description": overrides.get("description") or repo.get("description") or "",
        "tags": overrides.get("tags") or default_tags,
        "status": overrides.get("status", ""),
        "repo_url": repo["html_url"],
    }
    if not card["description"]:
        print(f"skip {repo['name']}: add a description in the repo's About section", file=sys.stderr)
        return None
    if not isinstance(card["tags"], list):
        card["tags"] = []
    return card


def main():
    found = get(f"{API}/search/repositories?q=user:{OWNER}+topic:portfolio&sort=updated&per_page=100")
    cards = [c for c in (load_card(r) for r in found["items"]) if c]
    with open("projects.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(cards)} project card(s) written to projects.json")


if __name__ == "__main__":
    main()
