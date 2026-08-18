"""Student record shared by the Excel loader and the form builders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DEFAULT_COORDINATOR_NAME = "Ugin KC"
DEFAULT_COORDINATOR_POSITION = "Placement Co-ordinator"
DEFAULT_DUTIES = "Please refer to the Job description provided by the student."


class PlacementType(Enum):
    FOE = "FOE"
    PROVIDER = "PROVIDER"


@dataclass(frozen=True)
class Student:

    placement_type: PlacementType
    participant_name: str
    program_name: str
    host_organisation: str
    host_address: str
    host_abn: str
    host_signatory_name: str
    supervisor_name: str
    start_date: str
    finish_date: str
    agreement_date: str
    host_signatory_position: str = ""
    attendance_hours: str = ""
    position_title: str = ""
    duties: str = DEFAULT_DUTIES
    mid_placement_date: str = ""
    coordinator_name: str = DEFAULT_COORDINATOR_NAME
    coordinator_position: str = DEFAULT_COORDINATOR_POSITION

    @property
    def host_signatory_full(self) -> str:
        if self.host_signatory_position:
            return f"{self.host_signatory_name} - {self.host_signatory_position}"
        return self.host_signatory_name
