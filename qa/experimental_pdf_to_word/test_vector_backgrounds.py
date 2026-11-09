from qa.experimental_pdf_to_word.vector_backgrounds import contrast_ratio
from qa.experimental_pdf_to_word.fixtures import generate_all


def test_contrast_ratio_matches_wcag_reference_values() -> None:
    assert round(contrast_ratio(0x000000, 0xFFFFFF), 1) == 21.0
    assert round(contrast_ratio(0xFFFFFF, 0x123C5F), 1) >= 10.0


def test_similar_colors_do_not_pass_header_contrast() -> None:
    assert contrast_ratio(0x707070, 0x777777) < 3.0


def test_phase2b_anonymous_fixture_matrix_is_generated(tmp_path) -> None:
    fixtures = generate_all(tmp_path)

    assert {
        "colored_headers",
        "alternating_fills",
        "borderless_boxes",
        "nested_table",
        "multipage",
        "four_column_form",
        "color_region_without_text",
    }.issubset(fixtures)
    assert all(path.exists() and path.stat().st_size > 0 for path in fixtures.values())
