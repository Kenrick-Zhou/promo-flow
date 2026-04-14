"""Build search_document and embedding_text for content records."""

from __future__ import annotations

_CONTENT_TYPE_LABELS: dict[str, str] = {
    "image": "图片 图像",
    "video": "视频 短视频",
}


def build_search_document(
    *,
    title: str | None,
    tag_names: list[str],
    ai_keywords: list[str],
    category_name: str | None,
    primary_category_name: str | None,
    content_type: str,
    description: str | None,
    ai_summary: str | None,
) -> str:
    """Build FTS search document with high-weight fields first.

    Field order (by weight):
      A: title, tag_names
      B: ai_keywords, category names, content_type label
      C: description, ai_summary
    """
    parts: list[str] = []

    if title:
        parts.append(title)
    if tag_names:
        parts.append(" ".join(tag_names))
    if ai_keywords:
        parts.append(" ".join(ai_keywords))
    if category_name:
        parts.append(category_name)
    if primary_category_name:
        parts.append(primary_category_name)

    type_label = _CONTENT_TYPE_LABELS.get(content_type)
    if type_label:
        parts.append(type_label)

    if description:
        parts.append(description)
    if ai_summary:
        parts.append(ai_summary)

    return " ".join(parts)


def build_embedding_text(
    *,
    title: str | None,
    description: str | None,
    tag_names: list[str],
    ai_keywords: list[str],
    ai_summary: str | None,
    primary_category_name: str | None,
    category_name: str | None,
    content_type: str,
) -> str:
    """Build text for embedding generation with full business context."""
    parts: list[str] = []

    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if tag_names:
        parts.append(" ".join(tag_names))
    if ai_keywords:
        parts.append(" ".join(ai_keywords))
    if ai_summary:
        parts.append(ai_summary)
    if primary_category_name:
        parts.append(primary_category_name)
    if category_name:
        parts.append(category_name)

    type_label = _CONTENT_TYPE_LABELS.get(content_type)
    if type_label:
        parts.append(type_label)

    return " ".join(parts)


def build_embedding_text_fallback(
    *,
    title: str | None,
    description: str | None,
    tag_names: list[str],
    category_name: str | None,
    primary_category_name: str | None,
    content_type: str,
) -> str | None:
    """Build fallback embedding text when AI analysis failed.

    Returns None if effective text length < 4 characters.
    """
    parts: list[str] = []
    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if tag_names:
        parts.append(" ".join(tag_names))
    if category_name:
        parts.append(category_name)
    if primary_category_name:
        parts.append(primary_category_name)

    type_label = _CONTENT_TYPE_LABELS.get(content_type)
    if type_label:
        parts.append(type_label)

    text = " ".join(parts).strip()
    if len(text) < 4:
        return None
    return text
