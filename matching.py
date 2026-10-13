import re
from difflib import SequenceMatcher
from datetime import datetime


DEFAULT_WEIGHTS = {
    "text": 0.45,
    "image": 0.25,
    "category": 0.15,
    "location": 0.10,
    "date": 0.05,
}


def _tokens(value):
    return set(re.findall(r"[a-z0-9]+", (value or "").casefold()))


def text_similarity(left, right):
    left = (left or "").strip().casefold()
    right = (right or "").strip().casefold()
    if not left or not right:
        return None
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    jaccard = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    sequence = SequenceMatcher(None, left, right).ratio()
    return min(1.0, 0.65 * jaccard + 0.35 * sequence)


def _date_score(left, right):
    if not left or not right:
        return None
    formats = (None, "Z")
    try:
        first = datetime.fromisoformat(str(left).replace("Z", "+00:00"))
        second = datetime.fromisoformat(str(right).replace("Z", "+00:00"))
    except ValueError:
        return None
    if first.tzinfo is None:
        first = first.replace(tzinfo=second.tzinfo)
    if second.tzinfo is None:
        second = second.replace(tzinfo=first.tzinfo)
    days = abs((first - second).total_seconds()) / 86400
    return max(0.0, 1.0 - days / 30.0)


def _location_score(left, right):
    a = _tokens(left)
    b = _tokens(right)
    if not a or not b:
        return None
    return len(a & b) / len(a | b)


def _category_score(left, right):
    if not left or not right:
        return None
    return 1.0 if left.strip().casefold() == right.strip().casefold() else 0.0


def compare_reports(lost_report, found_report, image_similarity=None, weights=None):
    configured = dict(DEFAULT_WEIGHTS)
    if weights:
        for key, value in weights.items():
            if key in configured and float(value) >= 0:
                configured[key] = float(value)

    left_text = " ".join(
        str(lost_report.get(key) or "")
        for key in ("item_name", "category", "description")
    )
    right_text = " ".join(
        str(found_report.get(key) or "")
        for key in ("item_name", "category", "description")
    )
    components = {
        "text": text_similarity(left_text, right_text),
        "image": (
            max(0.0, min(1.0, float(image_similarity)))
            if image_similarity is not None
            else None
        ),
        "category": _category_score(
            lost_report.get("category"),
            found_report.get("category"),
        ),
        "location": _location_score(
            lost_report.get("location"),
            found_report.get("location"),
        ),
        "date": _date_score(
            lost_report.get("created_at"),
            found_report.get("created_at"),
        ),
    }
    available_weight = sum(
        configured[key]
        for key, score in components.items()
        if score is not None
    )
    if available_weight == 0:
        return {"score": 0.0, "components": components, "explanations": []}

    score = sum(
        configured[key] * value
        for key, value in components.items()
        if value is not None
    ) / available_weight
    explanations = []
    if components["text"] is not None and components["text"] >= 0.2:
        explanations.append("item name or description has similar wording")
    if components["image"] is not None and components["image"] >= 0.65:
        explanations.append("photos look visually similar")
    if components["category"] == 1:
        explanations.append("categories match")
    if components["location"] is not None and components["location"] > 0:
        explanations.append("locations share words")
    if components["date"] is not None and components["date"] >= 0.5:
        explanations.append("reports were made within about 15 days")
    return {
        "score": score,
        "components": components,
        "explanations": explanations,
    }


def rank_lost_found_matches(reports, image_similarities=None, weights=None, limit=25):
    image_similarities = image_similarities or {}
    lost_reports = [
        row for row in reports
        if str(row.get("status", "")).casefold() in {"lost", "lost an item"}
        and not row.get("is_completed")
        and row.get("workflow_status") not in {"Returned", "Closed"}
    ]
    found_reports = [
        row for row in reports
        if str(row.get("status", "")).casefold() in {"found", "found an item"}
        and not row.get("is_completed")
        and row.get("workflow_status") not in {"Returned", "Closed"}
    ]
    matches = []
    for lost in lost_reports:
        for found in found_reports:
            if (
                lost.get("reporter_id") is not None
                and lost.get("reporter_id") == found.get("reporter_id")
            ):
                continue
            if lost.get("is_owner") and found.get("is_owner"):
                continue
            pair = (lost.get("id"), found.get("id"))
            result = compare_reports(
                lost,
                found,
                image_similarity=image_similarities.get(pair),
                weights=weights,
            )
            matches.append(
                {
                    "lost_report": lost,
                    "found_report": found,
                    **result,
                }
            )
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:limit]
