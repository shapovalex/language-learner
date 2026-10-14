"""R-13: the install and configuration docs say what the repo does.

Commands, config keys and the release asset URL in `docs/` and the README are read with regexes
and compared with pyproject, Settings and the files on disk, so a version bump, a renamed key or
a moved heading fails here until the docs follow.
"""

import re
import tomllib
from pathlib import Path

import pytest

from language_lab.settings import Settings
from tests.support.app_env import settings_env_names
from tests.support.release import PYPROJECT, REPO_ROOT, pyproject_version

pytestmark = pytest.mark.p2

DOCS = REPO_ROOT / "docs"
README = REPO_ROOT / "README.md"
INDEX = DOCS / "README.md"
INSTALL = DOCS / "install.md"
CONFIGURATION = DOCS / "configuration.md"
REMOTE_ACCESS = DOCS / "remote-access.md"
ANKI = DOCS / "anki.md"
DEVELOPMENT = DOCS / "development.md"

# Every page a user is sent to: all of docs/ plus the README that links into it.
PAGES = (README, *sorted(DOCS.glob("*.md")))

# The wheel release.yml attaches to the GitHub release of tag v<version>.
RELEASE_ASSET_URL = (
    "https://github.com/shapovalex/language-learner/releases/download/"
    "v{version}/language_lab-{version}-py3-none-any.whl"
)
# The only tailnet name the docs may show: a placeholder, never a real machine.
PLACEHOLDER_TAILNET_HOST = "mac-mini.tailnet-name.ts.net"

CONFIG_KEYS_HEADING = "Configuration keys"

# Each in-scope FR-4 item: (item, page, heading, what the text under the heading must say).
# A heading is renamed here and in the page together, on purpose.
FR4_MAP = [
    (
        "every configuration key explained",
        CONFIGURATION,
        CONFIG_KEYS_HEADING,
        ("env.example",),
    ),
    (
        "the one-time Tailscale Serve command",
        REMOTE_ACCESS,
        "Tailscale Serve command",
        ("tailscale serve --bg", "once"),
    ),
    (
        "any local process can control a keyless AnkiConnect",
        ANKI,
        "AnkiConnect has no key",
        ("no API key", "Any process"),
    ),
    (
        "study <Prefix>::Study, never the <Prefix> root",
        ANKI,
        "Study only the Study deck",
        ("study `<Prefix>::Study`", "Never study the `<Prefix>` root"),
    ),
    (
        "back up Anki before Setup or a migration",
        ANKI,
        "Back up before Setup or a migration",
        ("Make an Anki backup before",),
    ),
]

_FENCE = re.compile(r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_ENV_KEY = re.compile(r"(?<![A-Z0-9_])(?:LANGUAGE_LAB|ANKI|AZURE|OPENROUTER)_[A-Z0-9_]+")
_ASSET_URL = re.compile(r"https://github\.com/[^\s)`>]+/releases/download/[^\s)`>]+")
_TAILNET_HOST = re.compile(r"[A-Za-z0-9<>.-]+\.ts\.net")
_UVX = re.compile(r"\buvx --from \S+ (\S+)")
_SERVE_PORT = re.compile(r"\bserve --bg (\S+)")


def _name(page: Path) -> str:
    return page.relative_to(REPO_ROOT).as_posix()


def _text(page: Path) -> str:
    return page.read_text(encoding="utf-8")


def _shell_lines(text: str) -> list[str]:
    """Every line of the page's fenced `sh` blocks."""
    return [
        line
        for language, body in _FENCE.findall(text)
        if language == "sh"
        for line in body.splitlines()
    ]


def _prose(text: str) -> str:
    """The page with its fenced blocks blanked, so a `#` comment in a command is not a heading.

    Same length as `text`: an offset into one is an offset into the other.
    """
    return _FENCE.sub(lambda block: re.sub(r"[^\n]", " ", block.group(0)), text)


def _slug(heading: str) -> str:
    """The anchor GitHub gives a heading."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def _headings(text: str) -> list[str]:
    return [title for _, title in _HEADING.findall(_prose(text))]


def _section(text: str, heading: str) -> str | None:
    """The text under `heading`, up to the next heading of the same or a higher level.

    Code blocks included, and whitespace collapsed so a phrase is found across a line wrap.
    """
    prose = _prose(text)
    for match in _HEADING.finditer(prose):
        if match.group(2) != heading:
            continue
        level = len(match.group(1))
        end = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE).search(prose, match.end())
        return " ".join(text[match.end() : end.start() if end else len(text)].split())
    return None


def _relative_links(text: str) -> list[str]:
    return [
        target
        for target in _LINK.findall(_prose(text))
        if not target.startswith(("http://", "https://", "mailto:"))
    ]


def _console_scripts() -> set[str]:
    with PYPROJECT.open("rb") as f:
        return set(tomllib.load(f)["project"]["scripts"])


def _expected_asset_url() -> str:
    return RELEASE_ASSET_URL.format(version=pyproject_version())


class TestReleaseCommand:
    def test_install_page_gives_the_command_for_the_current_release(self) -> None:
        """Matrix: docs match repo. The command is the uvx line for this pyproject version."""
        (script,) = _console_scripts()

        assert f"uvx --from {_expected_asset_url()} {script}" in _shell_lines(_text(INSTALL))

    @pytest.mark.parametrize("page", PAGES, ids=_name)
    def test_no_page_names_another_release_asset(self, page: Path) -> None:
        """Matrix: version bump. A URL left at the old version is named in the failure."""
        expected = _expected_asset_url()

        stale = [url for url in _ASSET_URL.findall(_text(page)) if url != expected]

        assert stale == []

    def test_every_uvx_command_runs_the_console_script(self) -> None:
        scripts = _console_scripts()
        commands = [
            (_name(page), command)
            for page in PAGES
            for line in _shell_lines(_text(page))
            for command in _UVX.findall(line)
        ]

        assert _name(INSTALL) in {name for name, _ in commands}
        assert [found for found in commands if found[1] not in scripts] == []

    def test_development_page_runs_the_console_script_in_dev_mode(self) -> None:
        (script,) = _console_scripts()

        assert f"LANGUAGE_LAB_DEV=1 uv run {script}" in _shell_lines(_text(DEVELOPMENT))


class TestConfigurationKeys:
    @pytest.mark.parametrize("page", PAGES, ids=_name)
    def test_no_page_names_a_key_settings_lacks(self, page: Path) -> None:
        """Matrix: unknown key."""
        unknown = sorted(set(_ENV_KEY.findall(_text(page))) - settings_env_names())

        assert unknown == []

    def test_configuration_page_explains_every_settings_key(self) -> None:
        """Matrix: missing key. Each key has a row under the FR-4 heading."""
        section = _section(_text(CONFIGURATION), CONFIG_KEYS_HEADING) or ""
        rows = set(re.findall(r"\| `([A-Z][A-Z0-9_]*)` \|", section))

        assert sorted(settings_env_names() - rows) == []


class TestFr4Coverage:
    @pytest.mark.parametrize(
        ("page", "heading", "phrases"),
        [pytest.param(*row[1:], id=row[0]) for row in FR4_MAP],
    )
    def test_heading_states_the_item(
        self, page: Path, heading: str, phrases: tuple[str, ...]
    ) -> None:
        """Matrix: renamed heading. The id of the failing case is the FR-4 item."""
        section = _section(_text(page), heading)

        assert section is not None, f"{_name(page)} has no heading {heading!r}"
        assert [phrase for phrase in phrases if phrase not in section] == []

    @pytest.mark.parametrize(
        ("page", "heading"),
        [pytest.param(*row[1:3], id=row[0]) for row in FR4_MAP],
    )
    def test_index_links_to_the_heading(self, page: Path, heading: str) -> None:
        link = f"{page.name}#{_slug(heading)}"

        assert link in _relative_links(_text(INDEX))


class TestLinks:
    @pytest.mark.parametrize("page", PAGES, ids=_name)
    def test_relative_links_resolve(self, page: Path) -> None:
        """Matrix: broken link. A missing file or a missing heading anchor is named."""
        broken = []
        for link in _relative_links(_text(page)):
            path, _, anchor = link.partition("#")
            target = (page.parent / path).resolve() if path else page
            if not target.exists():
                broken.append(link)
            elif anchor and anchor not in {_slug(h) for h in _headings(_text(target))}:
                broken.append(link)

        assert broken == []

    def test_readme_links_to_every_docs_page(self) -> None:
        linked = {
            (REPO_ROOT / link.partition("#")[0]).resolve()
            for link in _relative_links(_text(README))
        }

        assert sorted(_name(page) for page in set(DOCS.glob("*.md")) - linked) == []


class TestRemoteAccess:
    def test_tailscale_serve_port_is_the_default_port(self) -> None:
        default_port = str(Settings.model_fields["port"].default)
        ports = [
            (_name(page), port)
            for page in PAGES
            for line in _shell_lines(_text(page))
            for port in _SERVE_PORT.findall(line)
        ]

        assert _name(REMOTE_ACCESS) in {name for name, _ in ports}
        assert [found for found in ports if found[1] != default_port] == []

    @pytest.mark.parametrize("page", PAGES, ids=_name)
    def test_only_the_placeholder_tailnet_name_appears(self, page: Path) -> None:
        hosts = set(_TAILNET_HOST.findall(_text(page)))

        assert sorted(hosts - {PLACEHOLDER_TAILNET_HOST}) == []
