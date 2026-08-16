"""Segmentation unit coverage (M4-2, #283): page markers, monotonic guard, cleaning."""

from __future__ import annotations

from quality_database_app.segment import page_marker_for, segment


def test_no_page_pattern_leaves_every_page_none() -> None:
    # source_id with no PAGE_MARKERS entry -> pattern None -> _page_by_line short-circuit.
    assert page_marker_for("some-source-with-no-markers") is None
    segs = segment("# Heading\n\nbody text\n", page_marker_for("some-source-with-no-markers"))
    # no page pattern -> every page is None (segment.py _page_by_line short-circuit)
    assert len(segs) == 1 and segs[0].clause == "Heading" and segs[0].page is None
    assert "body text" in segs[0].text


def test_out_of_order_digit_line_is_not_a_page_footer() -> None:
    # FMEA footer style '- N -'. A later marker whose number <= current is ignored
    # (the monotonic guard), so a stray/rewound digit cannot fabricate or reset a page.
    pattern = page_marker_for("fmea-vda-2019")
    text = "# A\nalpha\n- 5 -\n# B\nbeta\n- 3 -\n# C\ngamma\n- 9 -\n"
    segs = segment(text, pattern)
    pages = {s.clause: s.page for s in segs}
    assert pages["A"] == 5          # first footer closes page 5
    assert pages["B"] == 9          # '- 3 -' ignored (3 <= 5); next real footer is 9
    assert pages["C"] == 9


def test_heading_split_and_blank_prefix_dropped() -> None:
    # Text before the first heading that normalizes to empty is dropped (no clause, no body).
    text = "\n\n# Only\ncontent\n"
    segs = segment(text, None)
    assert [s.clause for s in segs] == ["Only"]


def test_prefix_before_first_heading_is_kept_with_none_clause() -> None:
    text = "preamble line\n\n# Head\nbody\n"
    segs = segment(text, None)
    assert segs[0].clause is None and "preamble" in segs[0].text
    assert segs[1].clause == "Head"
