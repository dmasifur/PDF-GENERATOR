# PDF Generator

Fills the Albright placement PDF forms from an Excel sheet, one folder of documents
per student.

## Usage

```bash
uv run pdfgenerator students.xlsx
```

Options:

| Flag | Default | Meaning |
|---|---|---|
| `--out` | `output` | Output directory |
| `--sheet` | first sheet | Worksheet name |
| `--batch` | today's date | Batch folder name |

Output layout:

```
output/2026-08-18/
├── Ada Lovelace/
│   ├── FOE Host Company Agreement.pdf
│   ├── Mid-Placement Report.pdf
│   └── Training Plan.pdf
└── Alan Turing/
    ├── Professional Year Host Company Agreement.pdf
    ├── Mid-Placement Report.pdf
    └── Training Plan.pdf
```

Because the batch folder defaults to today's date, re-running never overwrites a
previous day's output. Drag the batch folder into Google Drive when you're done.

## The two cases

| `Placement Type` | Agreement generated |
|---|---|
| `FOE` (also: `Found Own Employment`, `Case 1`) | FOE Host Company Agreement |
| `Provider` (also: `Provider Placed`, `Case 2`) | Professional Year Host Company Agreement |

Both cases also get the Mid-Placement Report and the Training Plan.

## Spreadsheet columns

One row per student. Headers are matched case-insensitively and ignore extra
whitespace, so minor header drift is fine.

**Required:** `Placement Type`, `Participant Name`, `Program Name`,
`Host Organisation`, `Host Address`, `Host ABN`, `Host Signatory Name`,
`Supervisor Name`, `Placement Start Date`, `Placement Finish Date`, `Agreement Date`

**Optional:** `Host Signatory Position`, `Attendance Hours`, `Position Title`,
`Duties`, `Mid Placement Date`, `Coordinator Name` (default `Ugin KC`),
`Coordinator Position` (default `Placement Co-ordinator`)

Dates can be real Excel date cells or strings (`07/09/2026`, `07-Sep-2026`,
`2026-09-07`). They are written into the PDFs as `07-Sep-2026`.

A row with a missing required value or an unreadable date is reported and skipped;
the rest of the batch still runs.

## What gets left blank

Output PDFs stay fillable. Signature boxes, comment areas, the monthly review
sections and the Training Plan's assessment checkboxes are all left empty for the
host, participant and coordinator to complete. The coordinator signature already
present in the templates is preserved.

## Notes for maintainers

Two things about these templates will surprise you. Both are covered by tests.

In `training_plan.pdf` the field named `Placement start date`
holds the *finish* date, and `Program commencement date` holds the *start* date. In
both agreements the FROM/TO fields are numbered in reverse. All mappings in
`forms.py` were derived from widget rectangles, not names — don't "fix" them to
match the names.

**Four FOE values aren't form fields.** The page-1 period dates and the page-5
annexure dates are `/FreeText` annotations someone typed with an annotation tool.
`filler.py` rewrites their appearance streams directly; they're matched by
rectangle, so if Albright reissues the template those coordinates need rechecking.


## Development

```bash
uv sync
uv run pytest
```
