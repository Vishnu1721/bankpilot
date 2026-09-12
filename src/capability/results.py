from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReplayStatus(str, Enum):
    SUCCESS = "success"
    BUSINESS_OUTCOME = "business_outcome"
    FAILURE = "failure"


class ReplayResult(BaseModel):
    status: ReplayStatus

    outputs: dict = Field(
        default_factory=dict
    )

    code: Optional[str] = None
    message: Optional[str] = None

    failed_step: Optional[str] = None
    expected: Optional[str] = None
    observed: Optional[str] = None

    recovered_steps: list[str] = Field(
        default_factory=list
    )

    evidence_path: Optional[str] = None