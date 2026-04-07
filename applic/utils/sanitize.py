import bleach

ALLOWED_TAGS = [
    'div', 'h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li',
    'span', 'strong', 'em', 'br',
]
ALLOWED_ATTRIBUTES = {
    'div':  ['class'],
    'span': ['class'],
    'p':    ['class'],
    'h1':   ['class'],
    'h2':   ['class'],
    'h3':   ['class'],
    'ul':   ['class'],
    'li':   ['class'],
}

def _sanitize_ai_html(raw_html: str) -> str:
    """Strip everything except the known-safe resume tags before PDF rendering."""
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
        strip_comments=True,
    )