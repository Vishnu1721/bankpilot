import json
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

    def __init__(
        self,
        parameters=None
    ):
        self.recorded_steps = []
        self.parameters = parameters or {}

    def set_parameters(
        self,
        parameters
    ):
        self.parameters = parameters or {}

    def record_action(
        self,
        action,
        observation
    ):
        if action.action not in (
            ActionType.TYPE,
            ActionType.CLICK
        ):
            return

        target = self._find_element(
            action.element_id,
            observation
        )

        if action.action == ActionType.TYPE:

            value = self._parameterize_value(
                action.value
            )

            step_type = StepType.TYPE

            description = (
                f"Enter value into "
                f"{target.name}."
            )

        else:

            value = None

            step_type = StepType.CLICK

            description = (
                f"Click {target.name}."
            )

        step = CapabilityStep(
            step_id=(
                f"step_"
                f"{len(self.recorded_steps) + 1}"
            ),
            action=step_type,
            target=TargetDefinition(
                role=target.role,
                name=target.name,
                selector=target.selector
            ),
            value=value,
            description=description
        )

        self.recorded_steps.append(
            step
        )

    def build_capability(
        self,
        start_url
    ):
        steps = list(
            self.recorded_steps
        )

        steps.append(
            CapabilityStep(
                step_id=(
                    f"step_"
                    f"{len(steps) + 1}"
                ),
                action=StepType.EXTRACT,
                target=None,
                value="Savings Balance",
                description=(
                    "Extract the current "
                    "savings balance."
                )
            )
        )

        capability = Capability(
            schema_version="1.0",

            capability_id=(
                "lookup_savings_balance"
            ),

            name=(
                "Lookup Savings Balance"
            ),

            description=(
                "Find a member and return "
                "their current savings balance."
            ),

            application="LegacyBank",

            start_url=start_url,

            parameters=[
                ParameterDefinition(
                    name="member_id",
                    type="string",
                    required=True,
                    description=(
                        "Member number "
                        "to search for."
                    )
                )
            ],

            outputs=[
                OutputDefinition(
                    name="savings_balance",
                    type="string",
                    description=(
                        "Current savings balance."
                    )
                )
            ],

            steps=steps,

            success_condition=(
                SuccessCondition(
                    type="text_present",
                    value="Member Details"
                )
            )
        )

        return capability

    def save(
        self,
        capability,
        path
    ):
        output = Path(path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with output.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                capability.model_dump(
                    mode="json"
                ),
                file,
                indent=2
            )

    def _find_element(
        self,
        element_id,
        observation
    ):
        for element in observation.elements:

            if (
                element.element_id
                == element_id
            ):
                return element

        raise ValueError(
            f"Element {element_id} "
            "was not found."
        )

    def _parameterize_value(
        self,
        value
    ):
        if value is None:
            return None

        for (
            parameter_name,
            parameter_value
        ) in self.parameters.items():

            if (
                str(value)
                == str(parameter_value)
            ):
                return (
                    "{{"
                    f"{parameter_name}"
                    "}}"
                )

        return value