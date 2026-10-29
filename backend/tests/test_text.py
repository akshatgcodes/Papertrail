from app.ingest.text import markdown_title, passages, split_long, split_spans

MD = """# Guide

Intro paragraph one. It has two sentences.

## Install

Run the installer. Then reboot.

Second para in install.

### Linux

Use apt.

## Usage
"""


def test_passages_follow_headings_and_offsets():
    ps = passages(MD, limit=300)
    assert [p.heading for p in ps] == ["Guide", "Guide › Install", "Guide › Install › Linux"]
    for p in ps:
        assert MD[p.start : p.end] == p.text
    assert ps[1].text == "Run the installer. Then reboot.\n\nSecond para in install."


def test_heading_levels_pop_back():
    md = "# A\n\n## B\n\nb text\n\n### C\n\nc text\n\n## D\n\nd text\n"
    assert [p.heading for p in passages(md)] == ["A › B", "A › B › C", "A › D"]


def test_skipped_levels():
    assert passages("### Deep\n\ntext here\n")[0].heading == "Deep"


def test_plain_text_ignores_hash_lines():
    ps = passages("# not a heading\n\nbody text\n", markdown=False)
    assert len(ps) == 1 and ps[0].heading == "" and ps[0].text.startswith("# not a heading")


def test_paragraphs_merge_up_to_the_limit():
    text = "\n\n".join(f"Paragraph number {i} has some words." for i in range(20))
    ps = passages(text, limit=120)
    assert len(ps) > 1
    assert all(len(p.text) <= 120 for p in ps)
    assert "".join(p.text for p in ps).count("Paragraph number") == 20


def test_long_paragraph_splits_at_sentences_with_overlap():
    sentence = "This sentence is about usage and keeps going. "
    text = (sentence * 20).strip()
    ps = passages(text, limit=200)
    assert len(ps) > 1 and all(len(p.text) <= 200 for p in ps)
    assert all(p.text.endswith(".") for p in ps)
    # Each piece starts with the previous piece's last sentence
    assert ps[1].start < ps[0].end


def test_split_spans_hard_splits_very_long_words():
    spans = split_spans("x" * 250, 100)
    assert [b - a for a, b in spans] == [100, 100, 50]
    assert split_long("Short. Text.", 100) == ["Short. Text."]


def test_markdown_title():
    assert markdown_title("intro\n# Title Here\n## Sub") == "Title Here"
    assert markdown_title("## only sub") is None


def test_blank_document():
    assert passages("\n\n   \n") == []
