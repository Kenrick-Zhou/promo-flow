"""Content type keyword dictionary for query understanding."""

CONTENT_TYPE_DICT: dict[str, list[str]] = {
    "video": ["视频", "短视频", "视频素材", "小视频"],
    "image": ["图片", "图", "海报", "照片", "图像", "banner"],
}

# Reverse lookup: keyword → content_type value
CONTENT_TYPE_KEYWORD_MAP: dict[str, str] = {
    keyword: content_type
    for content_type, keywords in CONTENT_TYPE_DICT.items()
    for keyword in keywords
}
