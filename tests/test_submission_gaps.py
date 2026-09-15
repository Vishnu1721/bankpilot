import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.agent.models import ActionType, AgentAction, Observation
from src.capability.models import Capability
from src.capability.registry import CapabilityEntry, CapabilityRegistry
from src.capability.replay import IdentityMismatchError, ReplayEngine
from src.safety.policy import SafetyPolicy, SafetyViolation


def test_single_output_mapping_is_inferred_before_contract_check():
    data = json.loads(Path("evidence/example_capability.json").read_text())
    extract = next(step for step in data["steps"] if step["action"] == "extract")
    extract.pop("output_name", None)
    capability = Capability.model_validate(data)
    assert next(step for step in capability.steps if step.action.value == "extract").output_name == "savings_balance"


def test_registry_never_persists_raw_goal_pii():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "registry.json"
        registry = CapabilityRegistry(path)
        registry.register(CapabilityEntry(
            capability_id="change_address",
            artifact_path="artifacts/change_address.json",
            application="LegacyBank Credit Union",
            intents=["Change Jane Doe SSN 123-45-6789 member address and reach review"],
        ))
        saved = path.read_text()
        assert "Jane Doe" not in saved
        assert "123-45-6789" not in saved
        assert "change" in saved and "address" in saved


def test_origin_policy_rejects_wrong_scheme_and_port():
    policy = SafetyPolicy()
    for url in ("http://127.0.0.1:5002/", "https://127.0.0.1:5001/"):
        try:
            policy.check_url(url)
            assert False, f"Expected blocked origin: {url}"
        except SafetyViolation:
            pass


def test_identity_and_amount_checks_are_meaningful():
    class Surface:
        def extract_labeled_value(self, _label):
            return "10025"

    engine = ReplayEngine.__new__(ReplayEngine)
    engine.surface = Surface()
    try:
        engine._verify_requested_identity({"member_id": "10024"})
        assert False, "Expected identity mismatch"
    except IdentityMismatchError:
        pass

    engine.recovered_steps = []
    capability = Capability.model_validate(
        json.loads(Path("artifacts/prepare_deposit.json").read_text())
    )
    result = engine._validate_business_inputs(capability, {"amount": "0"})
    assert result.code == "INVALID_AMOUNT"
    assert result.status.value == "business_outcome"


def test_discovery_budget_exhaustion_requests_handoff():
    class Page:
        url = "http://127.0.0.1:5001/"

        def title(self):
            return "LegacyBank Operations"

    class Surface:
        page = Page()

        def observe(self):
            return Observation(
                url=self.page.url,
                title=self.page.title(),
                text="Operations",
                elements=[],
            )

    class LLM:
        def decide(self, _goal, _observation):
            return AgentAction(action=ActionType.READ, reasoning="Inspect the page")

    class Handoff:
        calls = 0

        def handoff(self, reason, context):
            self.calls += 1
            return {
                "human_action": "Reviewed discovery dead end",
                "screenshot": "evidence/handoff_required.png",
            }

    handoff = Handoff()
    with TemporaryDirectory() as directory:
        agent = DiscoveryAgent(
            Surface(),
            budget=DiscoveryBudget(max_steps=1, max_llm_calls=1),
            llm=LLM(),
            handoff_manager=handoff,
            log_path=Path(directory) / "discovery.jsonl",
        )
        result = agent.run("Inspect workflow")
    assert handoff.calls == 1
    assert result["status"] == "human_intervention_completed"


if __name__ == "__main__":
    test_single_output_mapping_is_inferred_before_contract_check()
    test_registry_never_persists_raw_goal_pii()
    test_origin_policy_rejects_wrong_scheme_and_port()
    test_identity_and_amount_checks_are_meaningful()
    test_discovery_budget_exhaustion_requests_handoff()
    print("5/5 submission-gap tests passed")
