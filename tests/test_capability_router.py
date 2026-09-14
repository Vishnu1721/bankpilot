import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.agent.models import Observation
from src.capability.recorder import CapabilityRecorder
from src.capability.registry import CapabilityEntry, CapabilityRegistry
from src.capability.results import ReplayResult, ReplayStatus
from src.capability.router import CapabilityRouter, RouteMode


class FakeReplayEngine:
    def __init__(self):
        self.run_count = 0

    def load_capability(self, path):
        from src.capability.models import Capability
        return Capability.model_validate(json.loads(Path(path).read_text()))

    def run(self, capability, inputs):
        self.run_count += 1
        return ReplayResult(
            status=ReplayStatus.SUCCESS,
            outputs={"handled_member": inputs.get("member_id")},
            message="Replayed approved capability.",
        )


class FakeDiscoveryAgent:
    def __init__(self):
        self.run_count = 0

    def run(self, goal, artifact_path, parameters):
        self.run_count += 1
        observation = Observation(
            url="http://127.0.0.1:5001/address/review",
            title="Address Change Review",
            text="Address Change Review",
            elements=[],
        )
        recorder = CapabilityRecorder(parameters)
        capability = recorder.build_capability(
            "http://127.0.0.1:5001/",
            goal=goal,
            final_observation=observation,
        )
        recorder.save(capability, artifact_path)
        return {"status": "review_reached"}


def test_approved_match_replays_without_discovery(tmp_path):
    registry = CapabilityRegistry(tmp_path / "registry.json")
    fixture = Path("evidence/example_capability.json")
    registry.register(CapabilityEntry(
        capability_id="lookup_savings_balance",
        artifact_path=str(fixture),
        application="LegacyBank Credit Union",
        intents=["look up savings balance"],
    ))
    registry.approve("lookup_savings_balance", approved_by="test-reviewer")
    replay = FakeReplayEngine()
    discovery = FakeDiscoveryAgent()

    result = CapabilityRouter(registry, replay).execute(
        "Please look up member 10024 savings balance",
        {"member_id": "10024"},
        discovery_agent=discovery,
    )

    assert result.mode == RouteMode.REPLAYED
    assert result.replay_status == "success"
    assert replay.run_count == 1
    assert discovery.run_count == 0


def test_unknown_goal_discovers_once_then_requires_approval(tmp_path):
    registry = CapabilityRegistry(tmp_path / "registry.json")
    replay = FakeReplayEngine()
    discovery = FakeDiscoveryAgent()
    router = CapabilityRouter(registry, replay)
    artifact = tmp_path / "change_address.json"

    unknown = router.execute(
        "Change address for member 10023 and reach review",
        {"member_id": "10023", "address": "100 Demo Street"},
    )
    assert unknown.mode == RouteMode.DISCOVERY_REQUIRED

    created = router.execute(
        "Change address for member 10023 and reach review",
        {"member_id": "10023", "address": "100 Demo Street"},
        discovery_agent=discovery,
        artifact_path=artifact,
    )
    assert created.mode == RouteMode.DRAFT_CREATED
    assert discovery.run_count == 1
    assert replay.run_count == 0

    blocked = router.execute(
        "Change address for member 10024 and reach review",
        {"member_id": "10024", "address": "200 Demo Street"},
        discovery_agent=discovery,
        artifact_path=artifact,
    )
    assert blocked.mode == RouteMode.APPROVAL_REQUIRED
    assert discovery.run_count == 1
    assert replay.run_count == 0

    registry.approve(created.capability_id, approved_by="test-reviewer")
    replayed = router.execute(
        "Change address for member 10024 and reach review",
        {"member_id": "10024", "address": "200 Demo Street"},
        discovery_agent=discovery,
        artifact_path=artifact,
    )
    assert replayed.mode == RouteMode.REPLAYED
    assert replay.run_count == 1
    assert discovery.run_count == 1


def test_capabilities_are_isolated_by_tenant(tmp_path):
    registry = CapabilityRegistry(tmp_path / "registry.json")
    registry.register(CapabilityEntry(
        capability_id="lookup_savings_balance",
        artifact_path="evidence/example_capability.json",
        tenant_id="credit-union-a",
        application="LegacyBank Credit Union",
        intents=["look up savings balance"],
    ))
    registry.approve(
        "lookup_savings_balance",
        tenant_id="credit-union-a",
        approved_by="tenant-a-reviewer",
    )
    replay = FakeReplayEngine()
    router = CapabilityRouter(registry, replay)

    wrong_tenant = router.execute(
        "look up savings balance for member 10024",
        {"member_id": "10024"},
        tenant_id="credit-union-b",
    )
    assert wrong_tenant.mode == RouteMode.DISCOVERY_REQUIRED
    assert replay.run_count == 0


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        root = Path(directory)
        test_approved_match_replays_without_discovery(root / "known")
        test_unknown_goal_discovers_once_then_requires_approval(root / "unknown")
        test_capabilities_are_isolated_by_tenant(root / "tenants")
    print("3/3 capability router lifecycle tests passed")
