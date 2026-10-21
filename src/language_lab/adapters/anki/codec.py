"""The field codec (AD-9, AD-10): the only code that converts Anki field content.

Domain values are plain text. Writing escapes only `&`, `<` and `>` and turns each newline into
`<br>`. Reading turns `<br>` and block tags into newlines, strips every other tag, unescapes,
and maps NBSP to a space. `RussianAlternatives` is a list in the domain, joined with `", "`.
"""

import html
import re

_BLOCK_TAGS = "div|p|li|ul|ol|h[1-6]|blockquote|pre"
# A run of opening or closing block tags is one line boundary
_BLOCK_RUN = re.compile(rf"(?:<\s*/?\s*(?:{_BLOCK_TAGS})\b[^>]*>)+", re.IGNORECASE)
_BR = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]*>")
_NBSP = " "
_SEPARATOR = ", "


def encode_field(value: str) -> str:
    """A domain value as Anki field content: `& < >` escaped, each newline a `<br>`."""
    escaped = html.escape(value.replace("\r\n", "\n").replace("\r", "\n"), quote=False)
    return escaped.replace("\n", "<br>")


def decode_field(stored: str) -> str:
    """Anki field content as a plain-text domain value."""
    text = stored.replace("\r\n", "\n")

    def boundary(match: re.Match[str]) -> str:
        at_edge = match.start() == 0 or match.end() == len(text)
        return "" if at_edge else "\n"

    text = _BLOCK_RUN.sub(boundary, text)
    text = _BR.sub("\n", text)
    text = _TAG.sub("", text)
    return html.unescape(text).replace(_NBSP, " ")


def join_alternatives(alternatives: list[str]) -> str:
    """The `RussianAlternatives` list as one decoded field value."""
    return _SEPARATOR.join(alternatives)


def split_alternatives(stored: str) -> list[str]:
    """A decoded `RussianAlternatives` value as a list; tolerates hand edits made in Anki."""
    return [part.strip() for part in stored.split(",") if part.strip()]
