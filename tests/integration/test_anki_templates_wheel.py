"""Story 2.4: the card template and CSS files ship in the wheel the release builds (AD-3).

The manifest reads its templates from `adapters/anki/templates/` as package data, so a wheel
without them would leave Setup with nothing to create. The wheel is the one `release_wheel`
builds (or `--wheel`), and the manifest is then imported from it in uv's throwaway env, away
from `src/`.
"""

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

import language_lab.adapters.anki
from language_lab.adapters.anki.manifest import build_manifest
from tests.support.release import REPO_ROOT, run_python_from_wheel

SRC_ROOT = REPO_ROOT / "src"
TEMPLATES_DIR = Path(language_lab.adapters.anki.__file__).parent / "templates"

# Prints where the manifest was imported from and every template and CSS text it declares
_DUMP_MANIFEST = """
import json
from language_lab.adapters.anki import manifest
m = manifest.build_manifest("LanguageLab")
print(json.dumps({
    "file": manifest.__file__,
    "texts": {nt.name: [nt.css] + [s for t in nt.templates for s in (t.front, t.back)]
              for nt in m.note_types},
}))
"""


@pytest.mark.p1
def test_template_files_ship_in_the_built_wheel(release_wheel: Path, tmp_path: Path) -> None:
    """AC-9: every file under templates/ is in the wheel, and the installed manifest reads it."""
    source = {
        p.relative_to(SRC_ROOT).as_posix(): p.read_bytes()
        for p in TEMPLATES_DIR.rglob("*")
        if p.is_file()
    }
    with ZipFile(release_wheel) as wheel:
        names = set(wheel.namelist())
        missing = sorted(set(source) - names)
        shipped = {name: wheel.read(name) for name in source if name in names}

    assert source and missing == [], (sorted(source), missing)
    assert shipped == source
    installed = json.loads(run_python_from_wheel(release_wheel, _DUMP_MANIFEST, cwd=tmp_path))
    assert not Path(installed["file"]).is_relative_to(SRC_ROOT)  # the wheel, not src/
    expected = build_manifest("LanguageLab")
    assert installed["texts"] == {
        nt.name: [nt.css] + [s for t in nt.templates for s in (t.front, t.back)]
        for nt in expected.note_types
    }
