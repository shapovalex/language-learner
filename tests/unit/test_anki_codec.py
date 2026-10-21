"""Story 2.4: the field codec, the only code that converts Anki field content (AD-9, AD-10).

Domain values are plain text. Writing escapes only `&`, `<` and `>` and turns `\\n` into `<br>`.
Reading turns `<br>` and block tags into `\\n`, strips every other tag, unescapes, and maps NBSP
to a space, so markup the Anki editor adds never reaches the UI or the duplicate check.
`RussianAlternatives` is a list in the domain, joined with `", "` in Anki; only the codec joins
and splits it. Splitting tolerates the list after a hand edit in Anki.

Skipped until adapters/anki/codec.py exists. Un-skip a test, watch it fail, then implement.
Hoist the imports once it's green.
"""

import pytest

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.4: un-skip with adapters/anki/codec.py"
)

NBSP = " "

# (domain value, what is stored in the Anki field)
WRITES = [
    pytest.param("plain text", "plain text", id="plain"),
    pytest.param("l'été", "l'été", id="accents-and-apostrophe"),
    pytest.param('He said "hi"', 'He said "hi"', id="quotes-left-alone"),
    pytest.param("a < b & c > d", "a &lt; b &amp; c &gt; d", id="escapes"),
    pytest.param("<b>not bold</b>", "&lt;b&gt;not bold&lt;/b&gt;", id="markup-looking-text"),
    pytest.param("&amp; literally", "&amp;amp; literally", id="entity-looking-text"),
    pytest.param("one\ntwo\nthree", "one<br>two<br>three", id="newlines"),
    pytest.param("ends with\n", "ends with<br>", id="trailing-newline"),
    pytest.param("", "", id="empty"),
]

# (what the Anki editor or AnkiConnect left in a field, the domain value read from it)
READS = [
    pytest.param("one<br>two", "one\ntwo", id="br"),
    pytest.param("one<br/>two<br />three<BR>four", "one\ntwo\nthree\nfour", id="br-spellings"),
    pytest.param("one<br><br>two", "one\n\ntwo", id="blank-line"),
    pytest.param("one<div>two</div>", "one\ntwo", id="editor-div-line"),
    pytest.param("<div>one</div><div>two</div>", "one\ntwo", id="editor-div-lines"),
    pytest.param("<p>one</p><p>two</p>", "one\ntwo", id="paragraphs"),
    pytest.param("<ul><li>one</li><li>two</li></ul>", "one\ntwo", id="list"),
    pytest.param("<b>bold</b> and <i>it</i>", "bold and it", id="inline-tags-stripped"),
    pytest.param('<span style="color: rgb(0, 0, 0);">x</span>', "x", id="styled-span"),
    pytest.param("a &lt; b &amp; c &gt; d", "a < b & c > d", id="unescape"),
    pytest.param("&quot;q&quot; &#39;s&#39; &eacute;", "\"q\" 's' é", id="entities"),
    pytest.param("&amp;lt;b&amp;gt;", "&lt;b&gt;", id="double-escaped-once"),
    pytest.param("a&nbsp;b", "a b", id="nbsp-entity"),
    pytest.param(f"a{NBSP}b", "a b", id="nbsp-char"),
    pytest.param('He said "hi"<br>l\'été', 'He said "hi"\nl\'été', id="our-own-write"),
    pytest.param("", "", id="empty"),
]


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(("value", "stored"), WRITES)
def test_write_escapes_only_amp_lt_gt_and_turns_newlines_into_br(value: str, stored: str) -> None:
    """AC-10: no other markup is added, and reading the stored field gives the value back."""
    from language_lab.adapters.anki.codec import decode_field, encode_field

    assert encode_field(value) == stored
    assert decode_field(encode_field(value)) == value


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(("stored", "value"), READS)
def test_read_turns_anki_markup_into_plain_text(stored: str, value: str) -> None:
    """AC-11: `<br>` and block tags become newlines, other tags go, entities and NBSP resolve."""
    from language_lab.adapters.anki.codec import decode_field

    assert decode_field(stored) == value


@RED_PHASE
@pytest.mark.p1
def test_russian_alternatives_are_joined_and_split_with_comma_space() -> None:
    """AC-12: the list joins with ", " and splits back; a hand edit in Anki still splits."""
    from language_lab.adapters.anki.codec import join_alternatives, split_alternatives

    assert join_alternatives(["à la carte", "menu"]) == "à la carte, menu"
    assert split_alternatives("à la carte, menu") == ["à la carte", "menu"]
    assert join_alternatives(["seul"]) == "seul"
    assert split_alternatives("seul") == ["seul"]
    assert join_alternatives([]) == ""
    assert split_alternatives("") == []
    edited_in_anki = {
        "a,b": ["a", "b"],
        " a ,  b ": ["a", "b"],
        "a, , b,": ["a", "b"],
        "  ": [],
    }
    for stored, alternatives in edited_in_anki.items():
        assert split_alternatives(stored) == alternatives, stored
