"""Stream sources. A source exposes ``name`` and ``search(text) -> list[dict]``."""


class SourceError(Exception):
    """A source could not be queried; the message is shown to the user."""
