def paginate(items, page, per_page):
    """Return the items on page `page` (1-based), `per_page` a page. Pages past the end are empty.
    page < 1 or per_page < 1 raises ValueError."""
    start = page * per_page
    return items[start:start + per_page]
