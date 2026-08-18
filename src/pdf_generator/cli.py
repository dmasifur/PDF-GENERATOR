from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from .excel import load_students
from .filler import fill_pdf
from .forms import documents_for
from .models import Student

_UNSAFE = re.compile(r"[^\w\s.\-()&']", re.UNICODE)


def safe_folder_name(name: str) -> str:
    cleaned = _UNSAFE.sub("", name).strip(" .")
    cleaned = " ".join(cleaned.split())
    return cleaned or "unnamed"


def generate(student: Student, destination: Path) -> list[Path]:
    written: list[Path] = []
    for template, filename, fields, freetext in documents_for(student):
        output = destination / filename
        fill_pdf(template, output, fields, freetext or None)
        written.append(output)
    return written


class Args(argparse.Namespace):
    """The parsed command line, so ``args.<x>`` is typed rather than ``Any``."""

    spreadsheet: str
    out: str
    sheet: str | None
    batch: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdfgenerator",
        description="Fill Albright placement PDF forms from an Excel sheet.",
    )
    parser.add_argument("spreadsheet", help="path to the students .xlsx file")
    parser.add_argument(
        "--out", default="output", help="output directory (default: output)"
    )
    parser.add_argument(
        "--sheet", default=None, help="worksheet name (default: first sheet)"
    )
    parser.add_argument(
        "--batch",
        default=dt.date.today().isoformat(),
        help="batch folder name (default: today's date)",
    )
    args = parser.parse_args(argv, namespace=Args())

    source = Path(args.spreadsheet)
    if not source.exists():
        print(f"error: {source} not found", file=sys.stderr)
        return 1

    try:
        students, errors = load_students(str(source), args.sheet)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    batch_dir = Path(args.out) / args.batch
    total_files = 0

    for student in students:
        destination = batch_dir / safe_folder_name(student.participant_name)
        written = generate(student, destination)
        total_files += len(written)
        label = "FOE" if student.placement_type.name == "FOE" else "Provider"
        print(
            f"  {student.participant_name} [{label}] -> {destination}"
            f"  ({len(written)} files)"
        )

    print()
    print(
        f"Generated {len(students)} student(s), {total_files} file(s) into {batch_dir}"
    )
    sys.stdout.flush()

    if errors:
        print(f"\nSkipped {len(errors)} row(s):", file=sys.stderr)
        for error in errors:
            print(f"  row {error.row}: {error.reason}", file=sys.stderr)

    if not students:
        print("\nNothing generated.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
