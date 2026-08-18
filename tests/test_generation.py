from __future__ import annotations

from pathlib import Path
from typing import Any

from conftest import Cell, XlsxFactory
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, StreamObject

from pdf_generator.cli import main, safe_folder_name
from pdf_generator.filler import fill_pdf
from pdf_generator.forms import PY_TEMPLATE, TEMPLATE_DIR


def fields_of(path: Path) -> dict[str, Any]:
    """The PDF's form fields, asserting there are some."""
    fields = PdfReader(str(path)).get_fields()
    assert fields is not None, f"{path.name} has no form fields"
    return fields


def annotations_on(page: PageObject) -> list[DictionaryObject]:
    """The page's annotation dictionaries, resolved through any indirect references."""
    annots = page.get("/Annots")
    if annots is None:
        return []
    resolved = annots.get_object()
    assert isinstance(resolved, ArrayObject)
    return [
        annot
        for annot in (reference.get_object() for reference in resolved)
        if isinstance(annot, DictionaryObject)
    ]


def appearance_text(annot: DictionaryObject) -> str:
    """The decoded content of an annotation's normal appearance stream."""
    appearance = annot["/AP"].get_object()
    assert isinstance(appearance, DictionaryObject)
    stream = appearance["/N"].get_object()
    assert isinstance(stream, StreamObject)
    return stream.get_data().decode("latin-1", errors="replace")


def rendered_bytes(path: Path) -> str:
    """Everything a reader could see: field values plus every stream on every page.

    Field values alone are not enough - a widget renders its /AP appearance stream,
    so stale text can survive a blanked /V.
    """
    reader = PdfReader(str(path))
    chunks = [str(field.get("/V")) for field in (reader.get_fields() or {}).values()]

    seen: set[int] = set()

    def walk(obj: Any, depth: int = 0) -> None:
        if depth > 12:
            return
        obj = obj.get_object()
        if id(obj) in seen:
            return
        seen.add(id(obj))
        if isinstance(obj, StreamObject):
            chunks.append(obj.get_data().decode("latin-1", errors="replace"))
        if isinstance(obj, DictionaryObject):
            for value in obj.values():
                walk(value, depth + 1)
        elif isinstance(obj, ArrayObject):
            for value in obj:
                walk(value, depth + 1)

    for page in reader.pages:
        walk(page)
    return "\n".join(chunks)


def test_both_cases_produce_the_right_documents(
    both_cases_xlsx: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    assert main([str(both_cases_xlsx), "--out", str(out), "--batch", "b1"]) == 0

    ada = out / "b1" / "Ada Lovelace"
    alan = out / "b1" / "Alan Turing"

    assert (ada / "FOE Host Company Agreement.pdf").exists()
    assert not (ada / "Professional Year Host Company Agreement.pdf").exists()

    assert (alan / "Professional Year Host Company Agreement.pdf").exists()
    assert not (alan / "FOE Host Company Agreement.pdf").exists()

    for folder in (ada, alan):
        assert (folder / "Mid-Placement Report.pdf").exists()
        assert (folder / "Training Plan.pdf").exists()
        assert len(list(folder.glob("*.pdf"))) == 3


def test_foe_values_land_in_the_right_fields(foe_xlsx: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    main([str(foe_xlsx), "--out", str(out), "--batch", "b1"])

    fields = fields_of(out / "b1" / "Ada Lovelace" / "FOE Host Company Agreement.pdf")

    assert fields["Text1"]["/V"] == "Ada Lovelace"
    assert fields["Text2"]["/V"] == "Analytical Engines Pty Ltd"
    assert fields["Text3"]["/V"] == "1 Ada St, Sydney NSW 2000"
    assert fields["Text4"]["/V"] == "11 222 333 444"
    assert fields["Text5"]["/V"] == "PY in Engineering"
    assert fields["Text8"]["/V"] == "Charles Babbage"
    # Annexure keeps start and finish the right way round.
    assert fields["Text20"]["/V"] == "07-Sep-2026"
    assert fields["Text21"]["/V"] == "27-Nov-2026"
    assert fields["Text18"]["/V"] == "Grace Hopper"
    assert fields["Text26"]["/V"] == "Software Engineer"
    # Duties falls back to the template's standard sentence.
    assert "Job description" in fields["Text23"]["/V"]
    # Coordinator defaults.
    assert fields["Text9"]["/V"] == "Ugin KC"
    assert fields["Text10"]["/V"] == "Placement Co-ordinator"


def test_foe_freetext_dates_are_rewritten(foe_xlsx: Path, tmp_path: Path) -> None:
    """The page-1 period dates are annotations, not fields - they must still update."""
    out = tmp_path / "out"
    main([str(foe_xlsx), "--out", str(out), "--batch", "b1"])

    reader = PdfReader(
        str(out / "b1" / "Ada Lovelace" / "FOE Host Company Agreement.pdf")
    )
    freetext = [
        annot
        for annot in annotations_on(reader.pages[0])
        if annot.get("/Subtype") == "/FreeText"
    ]

    assert len(freetext) == 2
    contents = {str(a["/Contents"]) for a in freetext}
    assert contents == {"07-Sep-2026", "27-Nov-2026"}

    # The value must be in the appearance stream too, or it will not render.
    for annot in freetext:
        assert str(annot["/Contents"]) in appearance_text(annot)


def test_training_plan_date_fields_are_not_swapped(
    foe_xlsx: Path, tmp_path: Path
) -> None:
    """The template's field names are wrong; assert the rendered meaning is right."""
    out = tmp_path / "out"
    main([str(foe_xlsx), "--out", str(out), "--batch", "b1"])

    fields = fields_of(out / "b1" / "Ada Lovelace" / "Training Plan.pdf")

    # "Program commencement date" is the row rendered as "Placement start date".
    assert fields["Program commencement date"]["/V"] == "07-Sep-2026"
    assert fields["Placement start date"]["/V"] == "27-Nov-2026"
    assert fields["Participant name"]["/V"] == "Ada Lovelace"
    assert fields["SupervisorMentor name"]["/V"] == "Grace Hopper"


def test_provider_agreement_from_to_not_reversed(
    both_cases_xlsx: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    main([str(both_cases_xlsx), "--out", str(out), "--batch", "b1"])

    path = out / "b1" / "Alan Turing" / "Professional Year Host Company Agreement.pdf"
    fields = fields_of(path)

    assert fields["Text5"]["/V"] == "05-Oct-2026"  # FROM (left)
    assert fields["Text4"]["/V"] == "21-Dec-2026"  # TO (right)
    assert fields["Text7"]["/V"] == "Alan Turing"
    assert fields["Text6"]["/V"] == "John D - Manager"


def test_comment_and_signature_fields_stay_blank(
    both_cases_xlsx: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    main([str(both_cases_xlsx), "--out", str(out), "--batch", "b1"])

    fields = fields_of(out / "b1" / "Alan Turing" / "Mid-Placement Report.pdf")

    for name in ("Text10", "Text11", "Text12", "Text13", "Text14", "Text15"):
        assert not (fields[name].get("/V") or "")
    for name in ("Image1_af_image", "Image2_af_image", "Image3_af_image"):
        assert name in fields

    # Mid-placement date came from the spreadsheet for this student.
    assert fields["Text8"]["/V"] == "16-Nov-2026"


def test_output_is_still_fillable(foe_xlsx: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    main([str(foe_xlsx), "--out", str(out), "--batch", "b1"])

    for pdf in (out / "b1" / "Ada Lovelace").glob("*.pdf"):
        reader = PdfReader(str(pdf))
        root = reader.trailer["/Root"].get_object()
        assert isinstance(root, DictionaryObject)
        assert "/AcroForm" in root, f"{pdf.name} lost its form"
        assert reader.get_fields(), f"{pdf.name} has no fields left"


def test_training_plan_checkboxes_remain_unchecked(
    foe_xlsx: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    main([str(foe_xlsx), "--out", str(out), "--batch", "b1"])

    fields = fields_of(out / "b1" / "Ada Lovelace" / "Training Plan.pdf")
    checkboxes = [f for f in fields.values() if f.get("/FT") == "/Btn"]

    assert len(checkboxes) >= 22
    for box in checkboxes:
        assert box.get("/V") in (None, "/Off", "")


def test_batches_do_not_overwrite_each_other(foe_xlsx: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    main([str(foe_xlsx), "--out", str(out), "--batch", "2026-08-18"])
    main([str(foe_xlsx), "--out", str(out), "--batch", "2026-08-19"])

    assert (out / "2026-08-18" / "Ada Lovelace" / "Training Plan.pdf").exists()
    assert (out / "2026-08-19" / "Ada Lovelace" / "Training Plan.pdf").exists()


def test_safe_folder_name() -> None:
    assert safe_folder_name("Ada Lovelace") == "Ada Lovelace"
    assert safe_folder_name("Anne-Marie O'Brien") == "Anne-Marie O'Brien"
    assert safe_folder_name("Bad/Name:Here") == "BadNameHere"
    assert safe_folder_name("  spaced   out  ") == "spaced out"
    assert safe_folder_name("???") == "unnamed"


def test_no_data_leaks_between_students(make_xlsx: XlsxFactory, tmp_path: Path) -> None:
    """One participant's details must never appear in another participant's PDFs."""
    import datetime as dt

    def row(tag: str, kind: str) -> list[Cell]:
        return [
            kind, f"NAME{tag}", f"PROG{tag}", f"HOST{tag}", f"ADDR{tag}", f"ABN{tag}",
            f"SIGN{tag}", f"POSN{tag}", f"SUPER{tag}",
            dt.date(2026, 9, 7), dt.date(2026, 11, 27),
            f"HOURS{tag}", f"TITLE{tag}", f"DUTIES{tag}",
            dt.date(2026, 9, 1), dt.date(2026, 10, 1),
            f"COORD{tag}", f"CPOS{tag}",
        ]

    prefixes = ("NAME", "PROG", "HOST", "ADDR", "ABN", "SIGN", "POSN",
                "SUPER", "HOURS", "TITLE", "DUTIES", "COORD", "CPOS")

    out = tmp_path / "out"
    path = make_xlsx([row("AAA", "FOE"), row("BBB", "Provider")], name="two.xlsx")
    assert main([str(path), "--out", str(out), "--batch", "b1"]) == 0

    for mine, theirs in (("AAA", "BBB"), ("BBB", "AAA")):
        folder = out / "b1" / f"NAME{mine}"
        for pdf in sorted(folder.glob("*.pdf")):
            visible = rendered_bytes(pdf)
            # Negative control: this student's own data really is detectable, so a
            # clean result below cannot be the scan silently seeing nothing.
            assert f"NAME{mine}" in visible, f"{pdf.name} lost its own participant"
            found = [p + theirs for p in prefixes if p + theirs in visible]
            assert not found, f"{pdf.name} leaked {found} from the other student"


# The coordinator defaults are the one thing a template is meant to carry; the code
# re-fills them per student anyway.
INTENDED_DEFAULTS = {"Ugin", "KC", "Placement", "Co-ordinator"}


def template_residue() -> set[str]:
    """Every word still saved into a template's form fields."""
    residue: set[str] = set()
    for template in TEMPLATE_DIR.glob("*.pdf"):
        for field in (PdfReader(str(template)).get_fields() or {}).values():
            value = str(field.get("/V") or "").strip()
            if value and value != "/Off" and "Job description" not in value:
                residue.update(part for part in value.split() if len(part) > 3)
    return residue - INTENDED_DEFAULTS


def test_templates_carry_no_saved_participant_data() -> None:
    """The templates were built from completed forms; none may still hold a value.

    Deliberately name-free: it fails on *any* saved detail, so re-importing a
    filled-in form is caught without this file having to record whose data it was.
    """
    left = template_residue()
    assert not left, f"templates still carry saved values: {sorted(left)}"


def test_filling_clears_values_a_template_arrived_with(tmp_path: Path) -> None:
    """A value already in a template must not survive into output, even unmapped.

    Guards the blanking in fill_pdf: a widget renders its /AP appearance stream, so
    clearing /V alone would still print the old text. Poisons a throwaway copy of a
    template rather than relying on the shipped ones being dirty.
    """
    poisoned = tmp_path / "poisoned.pdf"
    reader = PdfReader(str(PY_TEMPLATE))
    writer = PdfWriter(clone_from=str(PY_TEMPLATE))
    names = sorted(reader.get_fields() or {})
    for page in writer.pages:
        writer.update_page_form_field_values(
            page, dict.fromkeys(names, "SENTINELVALUE"), auto_regenerate=False
        )
    with poisoned.open("wb") as handle:
        writer.write(handle)
    assert "SENTINELVALUE" in rendered_bytes(poisoned), "poisoning did not take"

    # Fill it setting only one field; every other field must still come out empty.
    out = tmp_path / "filled.pdf"
    fill_pdf(poisoned, out, {names[0]: "KEPT"})

    visible = rendered_bytes(out)
    assert "KEPT" in visible, "the value we did set went missing"
    assert "SENTINELVALUE" not in visible, "a pre-existing template value survived"


def test_templates_leave_no_residual_values_in_output(
    both_cases_xlsx: Path, tmp_path: Path
) -> None:
    """Nothing baked into a template may be inherited by a generated document."""
    out = tmp_path / "out"
    # Both placement types, so every template is actually exercised.
    assert main([str(both_cases_xlsx), "--out", str(out), "--batch", "b1"]) == 0

    generated = sorted((out / "b1").glob("*/*.pdf"))
    assert len(generated) == 6, "expected both students' full document sets"

    guarded = template_residue()
    for pdf in generated:
        visible = rendered_bytes(pdf)
        leaked = {word for word in guarded if word in visible}
        assert not leaked, f"{pdf.name} inherited template residue: {sorted(leaked)}"
