import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError

from src.agent.models import ActionType, AgentAction, Observation, UIElement
from src.capability.checkpoint import verify_observation_checkpoint
from src.capability.models import Capability, SuccessCondition
from src.capability.replay import ReplayEngine
from src.observability.logger import EventLogger
from src.handoff.manager import HumanHandoffManager
from src.safety.policy import SafetyPolicy, SafetyViolation


def expect_error(error_type, operation):
    try:
        operation()
        assert False, f"Expected {error_type.__name__}"
    except error_type:
        pass


def test_route_and_target_policy():
    policy = SafetyPolicy()
    expect_error(SafetyViolation, lambda: policy.check_url("http://127.0.0.1:5001/admin"))
    observation = Observation(
        url="http://127.0.0.1:5001/deposit/review",
        title="Deposit Review",
        text="Proceed",
        elements=[UIElement(element_id="e1", role="button", name="Proceed", selector="button")],
    )
    action = AgentAction(action=ActionType.CLICK, element_id="e1", reasoning="Proceed")
    expect_error(SafetyViolation, lambda: policy.check_action(action, observation))


def test_recursive_value_redaction():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "events.jsonl"
        logger = EventLogger(path)
        logger.log(
            "probe",
            reasoning="Member 10023 balance is $4,820.35 for Alex Morgan",
            outputs={"savings_balance": "$4,820.35"},
        )
        record = path.read_text()
        for secret in ("10023", "$4,820.35", "Alex Morgan"):
            assert secret not in record
        assert "[REDACTED" in record


def test_schema_and_input_types_are_enforced():
    data = json.loads(Path("evidence/example_capability.json").read_text())
    data["parameters"][0]["type"] = "anything"
    expect_error(ValidationError, lambda: Capability.model_validate(data))

    capability = Capability.model_validate(
        json.loads(Path("evidence/example_capability.json").read_text())
    )
    engine = ReplayEngine.__new__(ReplayEngine)
    expect_error(TypeError, lambda: engine._validate_inputs(capability, {"member_id": 10024}))


def test_unknown_checkpoint_and_false_finish_are_rejected():
    expect_error(
        ValidationError,
        lambda: SuccessCondition(type="unknown", value="Done"),
    )
    condition = SuccessCondition(type="text_present", value="Balance Result")
    observation = Observation(
        url="http://127.0.0.1:5001/balance-lookup",
        title="Balance Lookup",
        text="Balance Lookup form",
        elements=[],
    )
    expect_error(
        RuntimeError,
        lambda: verify_observation_checkpoint(condition, observation),
    )


def test_handoff_requires_description_and_changed_state():
    class Locator:
        def inner_text(self):
            return "Manual Verification Required"

    class Page:
        url = "http://127.0.0.1:5001/member"

        def title(self):
            return "Member Details"

        def locator(self, _selector):
            return Locator()

    class Surface:
        page = Page()

        def screenshot(self, _path):
            return None

    manager = HumanHandoffManager(Surface())
    with patch("builtins.input", return_value=""):
        expect_error(RuntimeError, lambda: manager.handoff("Verify member"))
    with patch("builtins.input", return_value="Completed verification"):
        expect_error(RuntimeError, lambda: manager.handoff("Verify member"))


if __name__ == "__main__":
    test_route_and_target_policy()
    test_recursive_value_redaction()
    test_schema_and_input_types_are_enforced()
    test_unknown_checkpoint_and_false_finish_are_rejected()
    test_handoff_requires_description_and_changed_state()
    print("5/5 hardening tests passed")
