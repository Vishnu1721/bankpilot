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


if __name__ == "__main__":
    test_declared_outputs_have_extraction_steps()
    print("4/4 capability output contracts passed")
