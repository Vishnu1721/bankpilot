from enum import Enum
from typing import Optional
from pydantic import BaseModel

class StepType(str, Enum):
    NAVIGATE = "navigate"
    TYPE = "type"
    SELECT = "select"
    CLICK = "click"
    EXTRACT = "extract"
    WAIT = "wait"

class ParameterDefinition(BaseModel):
    name: str
    type: str
    required: bool = True
    description: Optional[str] = None

class OutputDefinition(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class TargetDefinition(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = None
    selector: Optional[str] = None

class CapabilityStep(BaseModel):
    step_id: str
    action: StepType
    target: Optional[TargetDefinition] = None
    value: Optional[str] = None
    description: str

class SuccessCondition(BaseModel):
    type: str
    value: str

class Capability(BaseModel):
    schema_version: str
    capability_id: str
    name: str
    description: str
    application: str
    start_url: str
    parameters: list[ParameterDefinition]
    outputs: list[OutputDefinition]
    steps: list[CapabilityStep]
    success_condition: SuccessCondition
