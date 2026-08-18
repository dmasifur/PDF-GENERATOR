

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from .filler import FreeTextMap
from .models import PlacementType, Student

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"

FOE_TEMPLATE = TEMPLATE_DIR / "foe_host_company_agreement.pdf"
PY_TEMPLATE = TEMPLATE_DIR / "py_host_company_agreement.pdf"
MID_REVIEW_TEMPLATE = TEMPLATE_DIR / "mid_placement_report.pdf"
TRAINING_PLAN_TEMPLATE = TEMPLATE_DIR / "training_plan.pdf"

# FreeText annotation rectangles in the FOE template, keyed (page_index, rect).
FOE_PERIOD_FROM = (0, (177.0, 263.0, 327.0, 284.0))
FOE_PERIOD_TO = (0, (353.0, 262.0, 518.0, 283.0))
FOE_ANNEXURE_SUPERVISOR_DATE = (4, (103.0, 136.0, 260.0, 157.0))
FOE_ANNEXURE_PARTICIPANT_DATE = (4, (331.0, 136.0, 422.0, 157.0))


def build_foe(s: Student) -> dict[str, str]:
    return {
        # Page 1 - parties
        "Text1": s.participant_name,
        "Text2": s.host_organisation,
        "Text3": s.host_address,
        "Text4": s.host_abn,
        "Text5": s.program_name,
        # "I ___ verify that the participant is a paid employee"
        "Text8": s.host_signatory_name,
        # Page 4 - signature blocks
        "Text9": s.coordinator_name,
        "Text10": s.coordinator_position,
        "Text6": s.agreement_date,
        "Text12": s.host_organisation,
        "Text13": s.host_signatory_name,
        "Text7": s.agreement_date,
        "Text15": s.participant_name,
        "Text11": s.agreement_date,
        # Page 5 - annexure / training plan
        "Text17": s.participant_name,
        "Text18": s.supervisor_name,
        "Text19": s.host_organisation,
        "Text20": s.start_date,
        "Text21": s.finish_date,
        "Text22": s.attendance_hours,
        "Text26": s.position_title,
        "Text23": s.duties,
    }


def build_foe_freetext(s: Student) -> FreeTextMap:
    """The four FOE values that are annotations rather than form fields."""
    return {
        FOE_PERIOD_FROM: s.start_date,
        FOE_PERIOD_TO: s.finish_date,
        FOE_ANNEXURE_SUPERVISOR_DATE: s.agreement_date,
        FOE_ANNEXURE_PARTICIPANT_DATE: s.agreement_date,
    }


def build_py_agreement(s: Student) -> dict[str, str]:
    """Professional Year host agreement - 11 text fields on pages 1 and 5."""
    return {
        "Text1": s.host_organisation,
        "Text2": s.host_abn,
        "Text3": s.host_address,
        # FROM/TO are numbered in reverse; Text5 sits left (x=196), Text4 right (x=351).
        "Text5": s.start_date,
        "Text4": s.finish_date,
        # Page 5 - three signature blocks, each a name plus a date.
        "Text6": s.host_signatory_full,
        "Text9": s.agreement_date,
        "Text7": s.participant_name,
        "Text10": s.agreement_date,
        "Text8": s.coordinator_name,
        "Text11": s.agreement_date,
    }


def build_mid_review(s: Student) -> dict[str, str]:
    """Mid-placement report header block.

    Text10-Text15 (comments and their dates) and the Image*_af_image signature
    fields are intentionally left blank for the supervisor, participant and
    coordinator to complete by hand.
    """
    return {
        "Text1": s.participant_name,
        "Text2": s.supervisor_name,
        "Text3": s.host_organisation,
        "Text5": s.program_name,
        "Text6": s.start_date,
        "Text7": s.finish_date,
        "Text8": s.mid_placement_date,
        "Text9": s.coordinator_name,
    }


def build_training_plan(s: Student) -> dict[str, str]:
    """Training plan header block.

    Monthly review bodies, end-of-placement comments and the 22 assessment
    checkboxes are left blank for the supervisor.
    """
    return {
        "Participant name": s.participant_name,
        "SupervisorMentor name": s.supervisor_name,
        "Host Organisation": s.host_organisation,
        "Program name": s.program_name,
        # These two field names are wrong in the template - verified by widget
        # position. Do not swap them to match the names.
        "Program commencement date": s.start_date,  # renders as "Placement start date"
        "Placement start date": s.finish_date,  # renders as "Placement finish date"
        "Participant Name": s.participant_name,  # page 4, repeated
    }


class Document(NamedTuple):
    """One PDF to render for a student."""

    template: Path
    filename: str
    fields: dict[str, str]
    freetext: FreeTextMap


def documents_for(s: Student) -> list[Document]:
    """Every document a student needs."""
    if s.placement_type is PlacementType.FOE:
        agreement = Document(
            FOE_TEMPLATE,
            "FOE Host Company Agreement.pdf",
            build_foe(s),
            build_foe_freetext(s),
        )
    else:
        agreement = Document(
            PY_TEMPLATE,
            "Professional Year Host Company Agreement.pdf",
            build_py_agreement(s),
            {},
        )

    return [
        agreement,
        Document(
            MID_REVIEW_TEMPLATE, "Mid-Placement Report.pdf", build_mid_review(s), {}
        ),
        Document(
            TRAINING_PLAN_TEMPLATE, "Training Plan.pdf", build_training_plan(s), {}
        ),
    ]
