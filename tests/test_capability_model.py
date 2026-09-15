from src.capability.models import (
    Capability,
    CapabilityStep,
    OutputDefinition,
    ParameterDefinition,
    StepType,
    SuccessCondition,
    TargetDefinition,
)


def build_capability():
    return Capability(
    schema_version="1.1",
    capability_id="lookup_savings_balance",
    name="Lookup Savings Balance",
    description=(
        "Find a member and return "
        "their savings balance."
    ),
    application="LegacyBank",
    start_url="http://127.0.0.1:5001",

    parameters=[
        ParameterDefinition(
            name="member_id",
            type="string",
            description="Member number to search for."
        )
    ],

    outputs=[
        OutputDefinition(
            name="savings_balance",
            type="string",
            description="Current savings balance."
        )
    ],

    steps=[
        CapabilityStep(
            step_id="step_1",
            action=StepType.TYPE,
            target=TargetDefinition(
                role="textbox",
                name="Member Id",
                selector='input[name="member_id"]'
            ),
            value="{{member_id}}",
            description="Enter the member number."
        ),

        CapabilityStep(
            step_id="step_2",
            action=StepType.CLICK,
            target=TargetDefinition(
                role="button",
                name="Search",
                selector='button[type="submit"]'
            ),
            description="Submit the member search."
        ),

        CapabilityStep(
            step_id="step_3",
            action=StepType.EXTRACT,
            value="Savings Balance",
            description="Extract the savings balance."
        )
    ],

    success_condition=SuccessCondition(
        type="text_present",
        value="Member Details"
    )
    )


def test_single_output_mapping_inference():
    capability = build_capability()
    extract = next(step for step in capability.steps if step.action == StepType.EXTRACT)
    assert extract.output_name == "savings_balance"


if __name__ == "__main__":
    capability = build_capability()
    test_single_output_mapping_inference()
    print(
        capability.model_dump_json(
            indent=2
        )
    )
