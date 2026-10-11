"""Read the served shell's head: its viewport meta and the stylesheets it pulls in."""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

from fastapi.testclient import TestClient

_IMPORT = re.compile(r"""@import\s+(?:url\()?\s*["']?([^"')\s;]+)""")


@dataclass
class ShellHead:
    viewport: str = ""
    stylesheets: list[str] = field(default_factory=list)


class _HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.head = ShellHead()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "meta" and values.get("name") == "viewport":
            self.head.viewport = values.get("content", "")
        if tag == "link" and "stylesheet" in values.get("rel", "").split():
            self.head.stylesheets.append(values.get("href", ""))


def parse_shell(html: str) -> ShellHead:
    parser = _HeadParser()
    parser.feed(html)
    return parser.head


def viewport_directives(head: ShellHead) -> list[str]:
    """The viewport meta's comma-separated directives, spaces removed (`viewport-fit=cover`)."""
    return [part.strip().replace(" ", "") for part in head.viewport.split(",") if part.strip()]


def fetch_stylesheets(client: TestClient, page_path: str, head: ShellHead) -> str:
    """The text of every linked stylesheet and the sheets they `@import`, concatenated."""
    texts: list[str] = []
    seen: set[str] = set()
    pending = [urljoin(page_path, href) for href in head.stylesheets]
    while pending:
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        response = client.get(url)
        response.raise_for_status()
        texts.append(response.text)
        pending.extend(urljoin(url, ref) for ref in _IMPORT.findall(response.text))
    return "\n".join(texts)
