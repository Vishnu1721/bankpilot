from src.agent.models import (
    ActionType,
    AgentAction,
    Observation,
    UIElement
)

from src.capability.recorder import (
    CapabilityRecorder
)


recorder = CapabilityRecorder(
    parameters={
        "member_id": "72841"
    }
)


observation = Observation(
    url="http://127.0.0.1:5001",
    title="LegacyBank Admin",
    text="Member Search",
    elements=[
        UIElement(
            element_id="e1",
            role="textbox",
            name="Member Id",
            selector=(
                'input[name="member_id"]'
            ),
            value=""
        )
    ]
)


action = AgentAction(
    action=ActionType.TYPE,
    element_id="e1",
    value="72841",
    reasoning=(
        "Enter the requested member."
    )
)


recorder.record_action(
    action,
    observation
)


recorded_value = (
    recorder
    .recorded_steps[0]
    .value
)


print(
    "\nPARAMETERIZATION TEST"
)
print(
    "====================="
)

print(
    f"Runtime value: 72841"
)

print(
    f"Artifact value: "
    f"{recorded_value}"
)


assert (
    recorded_value
    == "{{member_id}}"
)


print(
    "\nPASS - runtime value was "
    "converted to {{member_id}}"
)