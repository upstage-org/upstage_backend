"""The text/plain alternative that `create_email` sends beside the HTML body."""

from upstage_backend.mails.helpers.mail import remove_html


def test_strips_tags_and_decodes_entities():
    html = '<p>Thank you,<br><b style="color: #007011">The UpStage Team!</b></p>'
    assert remove_html(html) == "Thank you,\nThe UpStage Team!\n"


def test_keeps_unicode_and_decodes_legacy_named_entities():
    # TinyMCE stored accents as named entities; tiptap stores the characters.
    assert remove_html("<p>caf&eacute; &amp; th&eacute;</p>") == "café & thé\n"
    assert remove_html("<p>Kia ora — 日本語 😀 עברית</p>") == "Kia ora — 日本語 😀 עברית\n"


def test_non_breaking_space_becomes_a_space():
    assert remove_html("<p>a&nbsp;b</p>") == "a b\n"


def test_empty_and_none():
    assert remove_html("") == ""
    assert remove_html(None) == ""
