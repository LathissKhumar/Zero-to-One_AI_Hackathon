from __future__ import annotations

from scripts.fetch_gutenberg_corpus import gutenberg_path, split_into_chapters, strip_gutenberg_boilerplate


def test_gutenberg_path_for_a_four_digit_id():
    assert gutenberg_path(1342) == "1/3/4/1342/1342-0.txt"


def test_gutenberg_path_for_a_two_digit_id():
    assert gutenberg_path(11) == "1/11/11-0.txt"
    assert gutenberg_path(84) == "8/84/84-0.txt"


def test_gutenberg_path_for_a_three_digit_id():
    assert gutenberg_path(345) == "3/4/345/345-0.txt"


def test_gutenberg_path_for_a_single_digit_id():
    assert gutenberg_path(4) == "0/4/4-0.txt"


def test_strip_gutenberg_boilerplate_removes_header_and_footer():
    raw = (
        "Some preamble line\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\n"
        "Real chapter one text here.\n"
        "Real chapter two text here.\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\n"
        "Some licence boilerplate.\n"
    )
    stripped = strip_gutenberg_boilerplate(raw)
    assert "preamble" not in stripped
    assert "licence boilerplate" not in stripped
    assert "Real chapter one text here." in stripped
    assert "Real chapter two text here." in stripped


def test_split_into_chapters_on_chapter_markers():
    text = (
        "CHAPTER I\n"
        "First chapter body sentence one. Sentence two.\n"
        "CHAPTER II\n"
        "Second chapter body sentence one. Sentence two.\n"
        "CHAPTER III\n"
        "Third chapter body sentence one. Sentence two.\n"
    )
    chapters = split_into_chapters(text)
    assert len(chapters) == 3
    assert "First chapter body" in chapters[0]
    assert "Second chapter body" in chapters[1]
    assert "Third chapter body" in chapters[2]


def test_split_into_chapters_falls_back_to_whole_text_when_no_markers_found():
    text = "Just one long block of prose with no chapter headings at all."
    chapters = split_into_chapters(text)
    assert chapters == [text]
