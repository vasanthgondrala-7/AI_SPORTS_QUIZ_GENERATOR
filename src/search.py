from duckduckgo_search import DDGS
from typing import List

def get_live_news_context(sport_name: str, max_results: int = 3) -> str:
    """Searches the live web for recent sport news and returns joined snippets."""
    if not sport_name:
        return ""

    query = f"{sport_name} latest tournament results championship winners news"
    retrieved = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            for i, r in enumerate(results, start=1):
                title = r.get("title", "")
                body = r.get("body", "")
                retrieved.append(f"Web Source {i}: {title}\nSnippet: {body}")
    except Exception as e:
        retrieved.append(f"[Web search failed: {e}]")

    return "\n\n".join(retrieved) if retrieved else "No recent web updates found."
