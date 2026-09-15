from enum import Enum
from typing import Optional
from pydantic import BaseModel, model_validator


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"


class SuccessConditionType(str, Enum):
    TEXT_PRESENT = "text_present"
    TITLE_EQUALS = "title_equals"
    URL_MATCHES = "url_matches"

class StepType(str, Enum):
    NAVIGATE = "navigate"
    TYPE = "type"
    SELECT = "select"
    CLICK = "click"
    EXTRACT = "extract"
    WAIT = "wait"

class ParameterDefinition(BaseModel):
    name: str
    type: DataType
    required: bool = True
    description: Optional[str] = None

class OutputDefinition(BaseModel):
    name: str
    type: DataType
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
    output_name: Optional[str] = None
    description: str

class SuccessCondition(BaseModel):
    type: SuccessConditionType
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

    @model_validator(mode="after")
    def validate_contract(self):
        if self.schema_version != "1.1":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        parameter_names = {item.name for item in self.parameters}
        output_names = {item.name for item in self.outputs}
        mapped_outputs = {
            step.output_name for step in self.steps
            if step.action == StepType.EXTRACT and step.output_name is not None
        }
        if len(parameter_names) != len(self.parameters) or len(output_names) != len(self.outputs):
            raise ValueError("Parameter and output names must be unique.")
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("Step IDs must be unique.")
        for step in self.steps:
            if step.action in {StepType.CLICK, StepType.TYPE, StepType.SELECT} and step.target is None:
                raise ValueError(f"{step.step_id} requires a target.")
            if step.action in {StepType.TYPE, StepType.SELECT} and step.value is None:
                raise ValueError(f"{step.step_id} requires a value.")
            if step.action == StepType.EXTRACT:
                if step.output_name is None and len(output_names) == 1:
                    step.output_name = next(iter(output_names))
                if step.output_name not in output_names:
                    raise ValueError(f"{step.step_id} must map to a declared output.")
            elif step.output_name is not None:
                raise ValueError("Only extract steps may declare output_name.")
            if step.value and step.value.startswith("{{") and step.value.endswith("}}"):
                name = step.value[2:-2]
                if name not in parameter_names:
                    raise ValueError(f"Undeclared parameter placeholder: {name}")
        missing_output_steps = output_names - mapped_outputs
        if missing_output_steps:
            raise ValueError(
                "Declared output(s) have no extraction step: "
                + ", ".join(sorted(missing_output_steps))
            )
        return self
