import json
import hashlib
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

    def build_capability(self, start_url, goal="", result=None, final_observation=None):
        goal_text = goal.lower()
        steps = list(self.recorded_steps)

        if "deposit" in goal_text:
            capability_id = "prepare_deposit"
            display_name = "Prepare Deposit"
            description = "Prepare a deposit and stop before funds are posted."
            outputs = [
                OutputDefinition(
                    name="amount",
                    type="string",
                    description="Deposit amount shown on the review screen.",
                )
            ]
            steps.append(CapabilityStep(
                step_id=f"step_{len(steps) + 1}", action=StepType.EXTRACT,
                target=None, value="Amount",
                description="Extract the reviewed deposit amount.",
            ))
            success = SuccessCondition(type="text_present", value="Deposit Review")

        elif "sub-account" in goal_text or "sub account" in goal_text:
            capability_id = "prepare_new_subaccount"
            display_name = "Prepare New Sub-account"
            description = "Prepare a new sub-account and stop before account creation."
            outputs = [
                OutputDefinition(
                    name="account_type",
                    type="string",
                    description="Account type shown on the confirmation review.",
                )
            ]
            steps.append(CapabilityStep(
                step_id=f"step_{len(steps) + 1}", action=StepType.EXTRACT,
                target=None, value="Account Type",
                description="Extract the reviewed sub-account type.",
            ))
            success = SuccessCondition(type="text_present", value="Review New Sub-account")

        elif "balance lookup" in goal_text:
            capability_id = "lookup_balance"
            display_name = "Lookup Balance"
            description = "Retrieve a selected account balance."
            outputs = [
                OutputDefinition(
                    name="current_balance",
                    type="string",
                    description="Current balance for the selected account.",
                )
            ]
            steps.append(CapabilityStep(
                step_id=f"step_{len(steps) + 1}", action=StepType.EXTRACT,
                target=None, value="Current Balance",
                description="Extract the selected account balance.",
            ))
            success = SuccessCondition(type="text_present", value="Balance Result")

        elif "member lookup" in goal_text or "member profile" in goal_text:
            capability_id = "lookup_member"
            display_name = "Lookup Member"
            description = "Find a member and display their account profile."
            outputs = [
                OutputDefinition(
                    name="member_name",
                    type="string",
                    description="Member name displayed by the lookup.",
                )
            ]
            steps.append(CapabilityStep(
                step_id=f"step_{len(steps) + 1}", action=StepType.EXTRACT,
                target=None, value="Member Name",
                description="Extract the member name.",
            ))
            success = SuccessCondition(type="text_present", value="Member Details")

        elif "savings" in goal_text and "balance" in goal_text:
            capability_id = "lookup_savings_balance"
            display_name = "Lookup Savings Balance"
            description = "Find a member and return their current savings balance."
            used_balance_lookup = any(
                step.target
                and step.target.name in {"Balance Lookup", "View Balance"}
                for step in steps
            )
            extraction_label = (
                "Current Balance" if used_balance_lookup else "Savings Balance"
            )
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
                    value=extraction_label,
                    description="Extract the current savings balance.",
                )
            )
            success = SuccessCondition(
                type="text_present",
                value="Balance Result" if used_balance_lookup else "Member Details",
            )

        else:
            normalized_goal = " ".join(re.findall(r"[a-z]+", goal_text))
            goal_hash = hashlib.sha256(normalized_goal.encode("utf-8")).hexdigest()[:8]
            capability_id = f"discovered_{goal_hash}"
            display_name = "Discovered Workflow"
            description = goal.strip() or "LLM-discovered workflow."
            outputs = []
            checkpoint = (
                final_observation.title
                if final_observation and final_observation.title
                else "Workflow Complete"
            )
            success = SuccessCondition(type="text_present", value=checkpoint)

        parameter_definitions = [
            ParameterDefinition(
                name=parameter_name,
                type="string",
                required=True,
                description=f"Runtime value for {parameter_name.replace('_', ' ')}.",
            )
            for parameter_name in self.parameters
        ]

        return Capability(
            schema_version="1.1",
            capability_id=capability_id,
            name=display_name,
            description=description,
            application="LegacyBank Credit Union",
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
