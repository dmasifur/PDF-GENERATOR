

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import FOE_ROW, PROVIDER_ROW, Cell, XlsxFactory

from pdf_generator.excel import load_students
from pdf_generator.models import PlacementType


def test_loads_both_placement_types(both_cases_xlsx: Path) -> None:
    students, errors = load_students(str(both_cases_xlsx))

    assert not errors
    assert [s.participant_name for s in students] == ["Ada Lovelace", "Alan Turing"]
    assert students[0].placement_type is PlacementType.FOE
    assert students[1].placement_type is PlacementType.PROVIDER


def test_dates_are_formatted_for_the_pdf(foe_xlsx: Path) -> None:
    students, _ = load_students(str(foe_xlsx))

    assert students[0].start_date == "07-Sep-2026"
    assert students[0].finish_date == "27-Nov-2026"
    assert students[0].agreement_date == "01-Sep-2026"


def test_defaults_fill_in_optional_columns(foe_xlsx: Path) -> None:
    students, _ = load_students(str(foe_xlsx))
    student = students[0]

    assert student.coordinator_name == "Ugin KC"
    assert student.coordinator_position == "Placement Co-ordinator"
    assert "Job description" in student.duties
    assert student.mid_placement_date == ""


@pytest.mark.parametrize(
    "value,expected",
    [
        ("FOE", PlacementType.FOE),
        ("foe", PlacementType.FOE),
        ("Found Own Employment", PlacementType.FOE),
        ("Case 1", PlacementType.FOE),
        ("Provider", PlacementType.PROVIDER),
        ("provider placed", PlacementType.PROVIDER),
        ("Case 2", PlacementType.PROVIDER),
    ],
)
def test_placement_type_aliases(
    make_xlsx: XlsxFactory, value: str, expected: PlacementType
) -> None:
    row: list[Cell] = list(FOE_ROW)
    row[0] = value
    students, errors = load_students(str(make_xlsx([row])))

    assert not errors
    assert students[0].placement_type is expected


def test_bad_row_is_skipped_and_batch_continues(make_xlsx: XlsxFactory) -> None:
    unknown_type: list[Cell] = list(FOE_ROW)
    unknown_type[0] = "Something Else"
    unknown_type[1] = "Broken One"

    missing_host: list[Cell] = list(FOE_ROW)
    missing_host[1] = "Broken Two"
    missing_host[3] = ""  # Host Organisation

    path = make_xlsx([unknown_type, PROVIDER_ROW, missing_host])
    students, errors = load_students(str(path))

    assert [s.participant_name for s in students] == ["Alan Turing"]
    assert len(errors) == 2
    assert "unrecognised" in errors[0].reason
    assert "Host Organisation" in errors[1].reason
    assert errors[0].row == 2 and errors[1].row == 4


def test_blank_spacer_rows_are_ignored(make_xlsx: XlsxFactory) -> None:
    path = make_xlsx([FOE_ROW, [None] * len(FOE_ROW), PROVIDER_ROW])
    students, errors = load_students(str(path))

    assert len(students) == 2
    assert not errors


def test_header_matching_is_forgiving(tmp_path: Path) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.append(
        [
            "  PLACEMENT TYPE ",
            "participant_name",
            "Program Name",
            "Host Organisation",
            "Host Address",
            "Host ABN",
            "Host Signatory Name",
            "Host Signatory Position",
            "Supervisor Name",
            "Placement Start Date",
            "Placement Finish Date",
            "Attendance Hours",
            "Position Title",
            "Duties",
            "Agreement Date",
            "Mid Placement Date",
            "Coordinator Name",
            "Coordinator Position",
        ]
    )
    sheet.append(list(FOE_ROW))
    path = tmp_path / "messy.xlsx"
    workbook.save(path)

    students, errors = load_students(str(path))
    assert not errors
    assert students[0].participant_name == "Ada Lovelace"


def test_string_dates_are_accepted(make_xlsx: XlsxFactory) -> None:
    row: list[Cell] = list(FOE_ROW)
    row[9] = "07/09/2026"
    row[10] = "27-Nov-2026"
    students, errors = load_students(str(make_xlsx([row])))

    assert not errors
    assert students[0].start_date == "07-Sep-2026"
    assert students[0].finish_date == "27-Nov-2026"


def test_unreadable_date_is_a_row_error(make_xlsx: XlsxFactory) -> None:
    row: list[Cell] = list(FOE_ROW)
    row[9] = "next tuesday"
    _, errors = load_students(str(make_xlsx([row])))

    assert len(errors) == 1
    assert "could not read date" in errors[0].reason


def test_missing_required_column_is_fatal(tmp_path: Path) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.worksheets[0].append(["Participant Name", "Program Name"])
    path = tmp_path / "bad.xlsx"
    workbook.save(path)

    with pytest.raises(ValueError, match="missing required column"):
        load_students(str(path))


def test_unknown_sheet_name_is_fatal(both_cases_xlsx: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        load_students(str(both_cases_xlsx), sheet="Nope")
