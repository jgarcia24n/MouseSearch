from difflib import SequenceMatcher
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - requirements include rapidfuzz.
    fuzz = None


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(v) for v in value.values() if v]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v]
    return [str(value)]


def candidate_validation_text(candidate: dict[str, Any]) -> str:
    parts = [
        candidate.get("title") or candidate.get("name") or "",
        " ".join(_string_list(candidate.get("author_names"))),
        candidate.get("author_name") or "",
        " ".join(_string_list(candidate.get("series_names"))),
    ]
    books = candidate.get("books")
    if isinstance(books, list):
        parts.extend(str(book.get("title") if isinstance(book, dict) else book) for book in books[:3])
    return " ".join(part for part in parts if part).strip()


def fuzzy_score(query: str, candidate_text: str) -> float:
    query = str(query or "").strip()
    candidate_text = str(candidate_text or "").strip()
    if not query or not candidate_text:
        return 0.0
    if fuzz is not None:
        return float(fuzz.token_set_ratio(query, candidate_text))
    return SequenceMatcher(None, query.lower(), candidate_text.lower()).ratio() * 100


def pick_valid_candidate(
    query: str,
    candidates: list[dict[str, Any]],
    threshold: float,
) -> tuple[dict[str, Any] | None, float, list[dict[str, Any]]]:
    scored = []
    for candidate in candidates:
        score = fuzzy_score(query, candidate_validation_text(candidate))
        scored.append({"candidate": candidate, "score": round(score, 1)})
        if score >= threshold:
            return candidate, round(score, 1), scored
    best_score = max((item["score"] for item in scored), default=0.0)
    return None, best_score, scored

