"""Studio tokens: what DESIGN.md declares, and what the app's CSS declares.

DESIGN.md's front matter is a plain YAML subset (nested maps of scalars), and the
project ships no YAML parser, so `load_front_matter` reads just that subset.
"""

import re
from pathlib import Path

DESIGN_MD = (
    Path(__file__).resolve().parents[2]
    / "_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md"
)

# DESIGN.md group -> custom-property prefix (decision, story 1.5 ATDD)
_GROUP_PREFIX = {"colors": "--color-", "spacing": "--space-", "rounded": "--radius-"}
# Typography role property -> custom-property stem; fontFamily is one family, not a token
_TYPE_PROPERTY = {
    "fontSize": "font-size",
    "fontWeight": "font-weight",
    "lineHeight": "line-height",
    "letterSpacing": "letter-spacing",
}

_CUSTOM_PROPERTY = re.compile(r"(--[A-Za-z0-9-]+)\s*:\s*([^;}]+)")
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def normalize(value: str) -> str:
    """Compare token values case- and quote-insensitively (`'#5A45C8'` == `#5a45c8`)."""
    return " ".join(_unquote(value).lower().split())


def load_front_matter(path: Path = DESIGN_MD) -> dict:
    """Parse the leading `---` block into nested dicts. List items are skipped."""
    lines = path.read_text(encoding="utf-8").splitlines()
    end = lines.index("---", 1)
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "- ")):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = stripped.partition(":")
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if value.strip():
            parent[_unquote(key)] = _unquote(value)
        else:
            child: dict = {}
            parent[_unquote(key)] = child
            stack.append((indent, child))
    return root


def expected_custom_properties(front_matter: dict) -> dict[str, str]:
    """The custom properties static/css must declare, with normalized values."""
    expected = {
        f"{prefix}{name}": normalize(value)
        for group, prefix in _GROUP_PREFIX.items()
        for name, value in front_matter[group].items()
    }
    for role, spec in front_matter["typography"].items():
        for prop, stem in _TYPE_PROPERTY.items():
            if prop in spec:
                expected[f"--{stem}-{role}"] = normalize(spec[prop])
    return expected


def css_custom_properties(css_dir: Path) -> dict[str, str]:
    """Every custom property declared in `css_dir/*.css` (normalized; a missing dir is empty)."""
    declared: dict[str, str] = {}
    for sheet in sorted(css_dir.glob("*.css")):
        text = _CSS_COMMENT.sub("", sheet.read_text(encoding="utf-8"))
        for name, value in _CUSTOM_PROPERTY.findall(text):
            declared[name] = normalize(value)
    return declared
