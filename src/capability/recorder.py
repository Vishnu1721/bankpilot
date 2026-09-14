import json
import re
from pathlib import Path

from src.agent.models import ActionType
from src.capability.models import (
    Capability,
    CapabilityStep,
    OutputDefinition,
    ParameterDefinition,
    StepType,
    SuccessCondition,
    TargetDefinition,
)


class CapabilityRecorder:

    def __init__(self, parameters=None):
        self.recorded_steps = []
        self.parameters = parameters or {}

    def set_parameters(self, parameters):
        self.parameters = parameters or {}

    def record_action(self, action, observation):
        action_map = {
            ActionType.TYPE: StepType.TYPE,
            ActionType.SELECT: StepType.SELECT,
            ActionType.CLICK: StepType.CLICK,
        }
        if action.action not in action_map:
            return

        target = self._find_element(action.element_id, observation)
        value = (
            self._parameterize_value(action.value)
            if action.action in {ActionType.TYPE, ActionType.SELECT}
            else None
        )
        verb = {
            ActionType.TYPE: "Enter value into",
            ActionType.SELECT: "Select a value for",
            ActionType.CLICK: "Click",
        }[action.action]

        self.recorded_steps.append(
            CapabilityStep(
                step_id=f"step_{len(self.recorded_steps) + 1}",
                action=action_map[action.action],
                target=TargetDefinition(
                    role=target.role,
                    name=target.name,
                    selector=target.selector,
                ),
                value=value,
                description=f"{verb} {target.name}.",
            )
        )

    def build_capability(self, start_url, goal="", result=None):
        is_subaccount = "sub-account" in goal.lower() or "sub account" in goal.lower()
        steps = list(self.recorded_steps)

        if is_subaccount:
            capability_id = "prepare_new_subaccount"
            name = "Prepare New Sub-account"
            description = "Prepare a new sub-account and stop at confirmation review."
            outputs = [
                OutputDefinition(
                    name="confirmation_status",
                    type="string",
                    description="Review status without committing the account.",
                )
            ]
            success = SuccessCondition(
                type="text_present",
                value="Review New Sub-account",
            )
        else:
            capability_id = "lookup_savings_balance"
            name = "Lookup Savings Balance"
            description = "Find a member and return their current savings balance."
            outputs = [
                OutputDefinition(
                    name="savings_balance",
                    type="string",
                    description="Current savings balance.",
                )
            ]
            steps.append(
                CapabilityStep(
                    step_id=f"step_{len(steps) + 1}",
                    action=StepType.EXTRACT,
                    target=None,
                    value="Savings Balance",
                    description="Extract the current savings balance.",
                )
            )
            success = SuccessCondition(type="text_present", value="Member Details")

        parameter_definitions = [
            ParameterDefinition(
                name=name,
                type="string",
                required=True,
                description=f"Runtime value for {name.replace('_', ' ')}.",
            )
            for name in self.parameters
        ]

        return Capability(
            schema_version="1.1",
            capability_id=capability_id,
            name=name,
            description=description,
            application="LegacyBank",
            start_url=start_url,
            parameters=parameter_definitions,
            outputs=outputs,
            steps=steps,
            success_condition=success,
        )

    def save(self, capability, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as file:
            json.dump(capability.model_dump(mode="json"), file, indent=2)

    @staticmethod
    def _find_element(element_id, observation):
        for element in observation.elements:
            if element.element_id == element_id:
                return element
        raise ValueError(f"Element {element_id} was not found.")

    def _parameterize_value(self, value):
        if value is None:
            return None
        for parameter_name, parameter_value in self.parameters.items():
            if str(value) == str(parameter_value):
                return "{{" + parameter_name + "}}"
        return value
