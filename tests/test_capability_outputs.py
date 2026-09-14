from src.capability.models import CapabilityStep, StepType, TargetDefinition
from src.capability.recorder import CapabilityRecorder


CASES = [
    ("member lookup for 10023", "member_name", "Member Name"),
    ("balance lookup for Savings", "current_balance", "Current Balance"),
    ("create a sub-account and reach review", "account_type", "Account Type"),
    ("prepare a deposit and reach review", "amount", "Amount"),
]


def test_declared_outputs_have_extraction_steps():
    for goal, output_name, label in CASES:
        capability = CapabilityRecorder().build_capability("http://127.0.0.1:5001", goal)
        assert capability.outputs[0].name == output_name
        assert capability.steps[-1].action.value == "extract"
        assert capability.steps[-1].value == label


def test_savings_goal_adapts_to_discovered_balance_lookup_page():
    recorder = CapabilityRecorder(parameters={"member_id": "10023"})
    recorder.recorded_steps = [
        CapabilityStep(
            step_id="step_1",
            action=StepType.CLICK,
            target=TargetDefinition(
                role="link",
                name="Balance Lookup",
                selector='a[aria-label="Balance Lookup"]',
            ),
            description="Open Balance Lookup.",
        )
    ]

    capability = recorder.build_capability(
        "http://127.0.0.1:5001",
        "Look up member 10023 and return their current savings balance.",
    )

    assert capability.outputs[0].name == "savings_balance"
    assert capability.steps[-1].value == "Current Balance"
    assert capability.success_condition.value == "Balance Result"


if __name__ == "__main__":
    test_declared_outputs_have_extraction_steps()
    test_savings_goal_adapts_to_discovered_balance_lookup_page()
    print("5/5 capability output contracts passed")
