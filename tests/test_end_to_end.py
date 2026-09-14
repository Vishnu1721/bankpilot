"""Canonical discovery -> artifact -> deterministic replay demonstration."""

from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.capability.replay import ReplayEngine
from src.surface.browser import BrowserSurface


START_URL = "http://127.0.0.1:5001"
ARTIFACT_PATH = "artifacts/lookup_savings_balance.json"


def main():
    discovery_surface = BrowserSurface(headless=False)
    try:
        discovery_surface.start()
        discovery_surface.navigate(START_URL)
        agent = DiscoveryAgent(
            discovery_surface,
            budget=DiscoveryBudget(max_steps=8, max_llm_calls=8),
            log_path="evidence/end_to_end_discovery.jsonl",
        )
        agent.run(
            goal="Look up member 10023 and return their current savings balance.",
            artifact_path=ARTIFACT_PATH,
            parameters={"member_id": "10023"},
        )
    finally:
        discovery_surface.close()

    replay_surface = BrowserSurface(headless=False)
    try:
        replay_surface.start()
        engine = ReplayEngine(
            replay_surface,
            log_path="evidence/end_to_end_replay.jsonl",
        )
        capability = engine.load_capability(ARTIFACT_PATH)
        result = engine.run(capability, inputs={"member_id": "10024"})
        replay_surface.screenshot("evidence/end_to_end_replay.png")
        assert result.outputs == {"savings_balance": "$2150.75"}, result
        print("\nEND-TO-END PASS")
        print(f"Artifact: {ARTIFACT_PATH}")
        print(f"Replay outputs: {result.outputs}")
    finally:
        replay_surface.close()


if __name__ == "__main__":
    main()
