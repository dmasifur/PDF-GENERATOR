from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import pytest
from openpyxl import Workbook

# A spreadsheet row as the fixtures write it: strings, real dates, and blanks.
Cell = str | dt.date | None
Row = Sequence[Cell]

HEADERS: list[str] = [
    "Placement Type",
    "Participant Name",
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

FOE_ROW: Row = [
    "FOE",
    "Ada Lovelace",
    "PY in Engineering",
    "Analytical Engines Pty Ltd",
    "1 Ada St, Sydney NSW 2000",
    "11 222 333 444",
    "Charles Babbage",
    "Director",
    "Grace Hopper",
    dt.date(2026, 9, 7),
    dt.date(2026, 11, 27),
    "Monday to Friday (38 Hours)",
    "Software Engineer",
    "",
    dt.date(2026, 9, 1),
    "",
    "",
    "",
]

PROVIDER_ROW: Row = [
    "Provider",
    "Alan Turing",
    "PY in Engineering",
    "Systems Pty Ltd",
    "2 Enigma Rd, Melbourne VIC 3000",
    "55 666 777 888",
    "John D",
    "Manager",
    "Max Newman",
    dt.date(2026, 10, 5),
    dt.date(2026, 12, 21),
    "",
    "",
    "",
    dt.date(2026, 10, 1),
    dt.date(2026, 11, 16),
    "",
    "",
]

def _write(path: Path, rows: Sequence[Row]) -> Path:
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.title = "Students"
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(list(row))
    workbook.save(path)
    return path


class XlsxFactory(Protocol):
    def __call__(self, rows: Sequence[Row], name: str = ...) -> Path: ...


@pytest.fixture
def both_cases_xlsx(tmp_path: Path) -> Path:
    return _write(tmp_path / "students.xlsx", [FOE_ROW, PROVIDER_ROW])


@pytest.fixture
def foe_xlsx(tmp_path: Path) -> Path:
    return _write(tmp_path / "foe.xlsx", [FOE_ROW])


@pytest.fixture
def make_xlsx(tmp_path: Path) -> XlsxFactory:
    def factory(rows: Sequence[Row], name: str = "custom.xlsx") -> Path:
        return _write(tmp_path / name, rows)

    return factory
