from src.agent.models import (
    ActionType,
    AgentAction,
    Observation,
    UIElement,
)

from src.capability.models import (
    Capability,
    CapabilityStep,
    OutputDefinition,
    ParameterDefinition,
    StepType,
    SuccessCondition,
    TargetDefinition,
)

from src.capability.recorder import (
    CapabilityRecorder,
)

from src.capability.replay import (
    ReplayEngine,
)

from src.safety.policy import (
    SafetyPolicy,
    SafetyViolation,
)


def test_parameterization():
    recorder = CapabilityRecorder(
        parameters={
            "member_id": "72841"
        }
    )

    observation = Observation(
        url="http://127.0.0.1:5001/member-search",
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
        reasoning="Test input."
    )

    recorder.record_action(
        action,
        observation
    )

    assert (
        recorder.recorded_steps[0].value
        == "{{member_id}}"
    )


def test_parameterization_is_not_hardcoded():
    recorder = CapabilityRecorder(
        parameters={
            "member_id": "55555"
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
        value="55555",
        reasoning="Test input."
    )

    recorder.record_action(
        action,
        observation
    )

    assert (
        recorder.recorded_steps[0].value
        == "{{member_id}}"
    )


def test_capability_schema():
    capability = Capability(
        schema_version="1.1",
        capability_id="test_capability",
        name="Test Capability",
        description="Validation capability.",
        application="LegacyBank",
        start_url="http://127.0.0.1:5001",

        parameters=[
            ParameterDefinition(
                name="member_id",
                type="string"
            )
        ],

        outputs=[
            OutputDefinition(
                name="savings_balance",
                type="string"
            )
        ],

        steps=[
            CapabilityStep(
                step_id="step_1",
                action=StepType.TYPE,

                target=TargetDefinition(
                    role="textbox",
                    name="Member Id",
                    selector=(
                        'input[name="member_id"]'
                    )
                ),

                value="{{member_id}}",
                description=(
                    "Enter member identifier."
                )
            ),
            CapabilityStep(
                step_id="step_2",
                action=StepType.EXTRACT,
                value="Savings Balance",
                output_name="savings_balance",
                description="Extract savings balance."
            )
        ],

        success_condition=(
            SuccessCondition(
                type="text_present",
                value="Member Details"
            )
        )
    )

    assert (
        capability.schema_version
        == "1.1"
    )

    assert (
        capability.parameters[0].name
        == "member_id"
    )

    assert (
        capability.steps[0].value
        == "{{member_id}}"
    )


def test_allowed_domain():
    policy = SafetyPolicy()

    policy.check_url(
        "http://127.0.0.1:5001"
    )


def test_blocked_domain():
    policy = SafetyPolicy()

    blocked = False

    try:
        policy.check_url(
            "https://example.com"
        )

    except SafetyViolation:
        blocked = True

    assert blocked is True


def test_safe_action():
    policy = SafetyPolicy()

    observation = Observation(
        url="http://127.0.0.1:5001/member-search",
        title="LegacyBank Admin",
        text="Member Search",
        elements=[
            UIElement(
                element_id="e1",
                role="button",
                name="Search Member",
                selector="button",
                value=None
            )
        ]
    )

    action = AgentAction(
        action=ActionType.CLICK,
        element_id="e1",
        reasoning="Search."
    )

    policy.check_action(
        action,
        observation
    )


def test_risky_action_blocked():
    policy = SafetyPolicy()

    observation = Observation(
        url="http://127.0.0.1:5001",
        title="LegacyBank Admin",
        text="Account",
        elements=[
            UIElement(
                element_id="e1",
                role="button",
                name="Delete Account",
                selector="button",
                value=None
            )
        ]
    )

    action = AgentAction(
        action=ActionType.CLICK,
        element_id="e1",
        reasoning="Delete."
    )

    blocked = False

    try:
        policy.check_action(
            action,
            observation
        )

    except SafetyViolation:
        blocked = True

    assert blocked is True


def test_template_resolution():
    engine = ReplayEngine.__new__(
        ReplayEngine
    )

    result = engine._resolve_value(
        "{{member_id}}",
        {
            "member_id": "10024"
        }
    )

    assert result == "10024"


def test_literal_resolution():
    engine = ReplayEngine.__new__(
        ReplayEngine
    )

    result = engine._resolve_value(
        "Savings Balance",
        {}
    )

    assert (
        result
        == "Savings Balance"
    )


def run_validation():
    tests = [
        (
            "Generic parameterization",
            test_parameterization
        ),
        (
            "No hardcoded member value",
            test_parameterization_is_not_hardcoded
        ),
        (
            "Capability schema",
            test_capability_schema
        ),
        (
            "Allowed domain",
            test_allowed_domain
        ),
        (
            "Blocked domain",
            test_blocked_domain
        ),
        (
            "Safe action",
            test_safe_action
        ),
        (
            "Risky action blocked",
            test_risky_action_blocked
        ),
        (
            "Template resolution",
            test_template_resolution
        ),
        (
            "Literal resolution",
            test_literal_resolution
        ),
    ]

    print(
        "\nBANKPILOT VALIDATION"
    )

    print(
        "===================="
    )

    passed = 0

    for name, test in tests:

        try:
            test()

            print(
                f"PASS - {name}"
            )

            passed += 1

        except Exception as error:

            print(
                f"FAIL - {name}"
            )

            print(
                f"       {error}"
            )

    print(
        "\n===================="
    )

    print(
        f"{passed}/{len(tests)} "
        "tests passed"
    )

    if passed != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    run_validation()
