import uuid


def parse_uuid(value: str) -> uuid.UUID | None:
    """Parse any UUID spelling (upper case, no hyphens, braces). None if malformed."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None
