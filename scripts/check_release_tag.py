"""Release guard: fail unless the pushed tag is exactly v<pyproject version>.

Usage: python scripts/check_release_tag.py <tag>

release.yml runs this before anything is built. Exits 0 when the tag matches, 1 when it
doesn't, and 2 on bad usage (no tag, an empty tag, or more than one). Stdlib only; reads
the pyproject.toml next to this repo.
"""

import sys
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
USAGE = "usage: check_release_tag.py <tag>"


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not argv[0]:
        print(USAGE, file=sys.stderr)
        return 2
    (tag,) = argv
    with PYPROJECT.open("rb") as f:
        version = tomllib.load(f)["project"]["version"]
    if tag == f"v{version}":
        print(f"Release tag {tag} matches pyproject version {version}")
        return 0
    print(f"Release tag {tag} does not match pyproject version {version} (expected v{version})")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
