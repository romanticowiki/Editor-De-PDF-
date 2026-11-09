from dataclasses import dataclass

from qa.experimental_pdf_to_word.merge_repair import repair_table_merges


@dataclass
class FakeCell:
    merged_cells: tuple[int, int] = (1, 1)
    active: bool = True

    def __bool__(self) -> bool:
        return self.active


class FakeTable(list):
    @property
    def num_rows(self) -> int:
        return len(self)

    @property
    def num_cols(self) -> int:
        return len(self[0])


def empty_table(rows: int, columns: int) -> FakeTable:
    return FakeTable([[FakeCell(active=False) for _ in range(columns)] for _ in range(rows)])


def test_overlapping_vertical_merge_is_limited_before_later_anchor() -> None:
    table = empty_table(6, 4)
    table[0][0] = FakeCell((5, 4))
    table[3][0] = FakeCell((2, 4))

    changes = repair_table_merges(table, "fixture")

    assert table[0][0].merged_cells == (3, 4)
    assert table[3][0].merged_cells == (2, 4)
    assert len(changes) == 1


def test_crossing_merge_is_resolved_without_changing_later_region() -> None:
    table = empty_table(5, 5)
    table[0][2] = FakeCell((4, 2))
    table[2][1] = FakeCell((2, 4))

    changes = repair_table_merges(table, "fixture")

    assert table[0][2].merged_cells == (2, 2)
    assert table[2][1].merged_cells == (2, 4)
    assert len(changes) == 1


def test_non_overlapping_and_legitimate_regions_are_unchanged() -> None:
    table = empty_table(5, 5)
    table[0][0] = FakeCell((2, 2))
    table[0][2] = FakeCell((2, 3))
    table[2][0] = FakeCell((3, 5))

    assert repair_table_merges(table, "fixture") == []
    assert table[0][0].merged_cells == (2, 2)
    assert table[0][2].merged_cells == (2, 3)
    assert table[2][0].merged_cells == (3, 5)
