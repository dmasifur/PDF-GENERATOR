"""Generic AcroForm filling for the Albright templates."""

from __future__ import annotations

from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    PdfObject,
    TextStringObject,
)

# A page-1-style value that has no form field behind it, keyed by the page index and
# the annotation rectangle it occupies.
FreeTextMap = dict[tuple[int, tuple[float, ...]], str]

# A FreeText rect is matched to within this many points, so tiny coordinate
# differences between template revisions do not break the lookup.
RECT_TOLERANCE = 2.0

FREETEXT_FONT_SIZE = 10.0
FREETEXT_PADDING_X = 3.0
FREETEXT_DESCENDER = 4.0


def _escape_pdf_text(text: str) -> str:
    """Escape a string for use inside a PDF literal string ``(...)``."""
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _annotations(page: PageObject) -> list[PdfObject]:
    annots = page.get("/Annots")
    if annots is None:
        return []
    resolved = annots.get_object()
    if not isinstance(resolved, ArrayObject):
        return []
    return list(resolved)


def _write_freetext(
    writer: PdfWriter, annot: DictionaryObject, rect: tuple[float, ...], text: str
) -> None:
    """Set the annotation's value and build the appearance stream that renders it."""
    annot[NameObject("/Contents")] = TextStringObject(text)

    width = rect[2] - rect[0]
    height = rect[3] - rect[1]

    baseline = max((height - FREETEXT_FONT_SIZE) / 2 + FREETEXT_DESCENDER, 1.0)
    stream = (
        f"q BT /Helv {FREETEXT_FONT_SIZE} Tf 0 g "
        f"{FREETEXT_PADDING_X} {baseline:.2f} Td "
        f"({_escape_pdf_text(text)}) Tj ET Q"
    )

    appearance = DecodedStreamObject()
    appearance.set_data(stream.encode("latin-1", errors="replace"))
    appearance[NameObject("/Type")] = NameObject("/XObject")
    appearance[NameObject("/Subtype")] = NameObject("/Form")
    appearance[NameObject("/FormType")] = NameObject("/1")
    appearance[NameObject("/BBox")] = ArrayObject(
        [FloatObject(0), FloatObject(0), FloatObject(width), FloatObject(height)]
    )

    resources = DictionaryObject()
    fonts = DictionaryObject()
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font[NameObject("/Encoding")] = NameObject("/WinAnsiEncoding")
    fonts[NameObject("/Helv")] = writer._add_object(font)
    resources[NameObject("/Font")] = fonts
    appearance[NameObject("/Resources")] = resources

    appearance_dict = DictionaryObject()
    appearance_dict[NameObject("/N")] = writer._add_object(appearance)
    annot[NameObject("/AP")] = appearance_dict

    annot[NameObject("/DA")] = TextStringObject(f"/Helv {FREETEXT_FONT_SIZE} Tf 0 g")


def set_freetext(
    writer: PdfWriter, page_index: int, rect: tuple[float, ...], text: str
) -> bool:
    page = writer.pages[page_index]
    existing = _annotations(page)

    for reference in existing:
        annot = reference.get_object()
        if not isinstance(annot, DictionaryObject):
            continue
        if annot.get("/Subtype") != "/FreeText":
            continue

        bounds = annot.get("/Rect")
        if not isinstance(bounds, ArrayObject) or len(bounds) != len(rect):
            continue

        current = tuple(float(value) for value in bounds)
        if any(
            abs(a - b) > RECT_TOLERANCE for a, b in zip(current, rect, strict=True)
        ):
            continue

        _write_freetext(writer, annot, current, text)
        return True

    # The templates carry no FreeText annotations of their own - these values sit on
    # printed lines with no form field behind them - so create the annotation.
    annot = DictionaryObject()
    annot[NameObject("/Type")] = NameObject("/Annot")
    annot[NameObject("/Subtype")] = NameObject("/FreeText")
    annot[NameObject("/Rect")] = ArrayObject([FloatObject(value) for value in rect])
    annot[NameObject("/F")] = NumberObject(4)  # print
    annot[NameObject("/Border")] = ArrayObject(
        [NumberObject(0), NumberObject(0), NumberObject(0)]
    )
    _write_freetext(writer, annot, rect, text)

    page[NameObject("/Annots")] = ArrayObject([*existing, writer._add_object(annot)])
    return True


def fill_pdf(
    template: Path,
    output: Path,
    values: dict[str, str],
    freetext: FreeTextMap | None = None,
) -> None:

    reader = PdfReader(str(template))
    writer = PdfWriter(clone_from=str(template))

    fill: dict[str, str] = {name: "" for name in reader.get_fields() or {}}
    fill.update(values)

    for page in writer.pages:
        writer.update_page_form_field_values(page, fill, auto_regenerate=False)

    for (page_index, rect), text in (freetext or {}).items():
        set_freetext(writer, page_index, rect, text)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)
