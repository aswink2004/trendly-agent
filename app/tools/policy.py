from pathlib import Path


POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "trendly_policy.md"
)


def load_policy() -> str:
    """
    Load the Trendly policy document.

    This file is the only source of truth for policy questions.
    """
    return POLICY_PATH.read_text(encoding="utf-8")


def search_policy(query: str) -> dict:
    """
    Search the supplied Trendly policy using simple local retrieval.

    No web search or external knowledge is used.
    """

    policy = load_policy()

    query_terms = [
        word.lower()
        for word in query.split()
        if len(word) > 2
    ]

    lines = policy.splitlines()

    matches = []

    for index, line in enumerate(lines):
        line_lower = line.lower()

        score = sum(
            term in line_lower
            for term in query_terms
        )

        if score > 0:
            start = max(0, index - 2)
            end = min(len(lines), index + 4)

            context = "\n".join(
                lines[start:end]
            )

            matches.append(
                (score, index, context)
            )

    matches.sort(
        key=lambda item: (-item[0], item[1])
    )

    results = [
        match[2]
        for match in matches[:5]
    ]

    return {
        "query": query,
        "found": len(results) > 0,
        "matches": results,
        "source": "trendly_policy.md",
    }