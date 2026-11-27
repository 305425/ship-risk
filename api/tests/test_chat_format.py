from app.assistant import format_chat_answer

SAMPLE = """
Vessels requiring intervention (start here)
1) MV Orion (V021)
Why intervention is needed: Highest fleet risk (Score 49.0, Band High). It also has 2 open deficiencies.
What to do first (priority):
Renew/complete crew training or plan relief (due 2026-12-03): “Renew STCW certificate (C0241)” [actions
].
Then pre-inspection readiness review (due 2026-12-10): “Pre-inspection readiness review (INS0086)” [actions].
Open deficiency context: MV Orion has 2 open deficiencies [open_items_by_vessel
].
Cross-vessel “what to do first” (pattern)
For these highest-risk vessels, the earliest intervention is:
Crew compliance action due 2026-12-03 [actions][actions].
Superintendent pre-inspection review due 2026-12-10 [actions].
"""


def test_plain_brief_becomes_markdown_without_tool_tags():
    rendered = format_chat_answer(SAMPLE)
    assert rendered.startswith("### Vessels requiring intervention")
    assert "1. **MV Orion (V021)**" in rendered
    assert "**Why intervention is needed.** Highest fleet risk" in rendered
    assert "- Renew/complete crew training" in rendered
    assert "- Then pre-inspection readiness review" in rendered
    assert "### Cross-vessel" in rendered
    assert "- Crew compliance action" in rendered
    assert "[actions]" not in rendered
    assert "open_items_by_vessel" not in rendered
    assert "`C0241`" not in rendered  # the id was already in parentheses, not a bracket cite


def test_markdown_answer_keeps_its_structure():
    source = "### High risk\n\n1. **MV Orion (V021)** is High.\n"
    assert format_chat_answer(source) == source.strip()


def test_record_citation_becomes_code():
    assert format_chat_answer("See [deficiencies:DEF0010].") == "See `deficiencies:DEF0010`."
