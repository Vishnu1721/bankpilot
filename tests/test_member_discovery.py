from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.surface.browser import BrowserSurface

GOAL = (
    "From the operations dashboard, use Member Lookup to find member 10023 "
    "and finish when Member Details are displayed."
)
surface = BrowserSurface(headless=False)

try:
    surface.start()
    surface.navigate("http://127.0.0.1:5001")
    result = DiscoveryAgent(
        surface=surface,
        budget=DiscoveryBudget(max_steps=6, max_llm_calls=6, max_elapsed_seconds=60),
        log_path="evidence/member_discovery.jsonl",
    ).run(
        goal=GOAL,
        artifact_path="artifacts/lookup_member.json",
        parameters={"member_id": "10023"},
    )
    print(result)
    surface.screenshot("evidence/member_details.png")
    input("\nPress Enter to close...")
except Exception as error:
    print(f"\nDISCOVERY FAILED: {error}")
    surface.screenshot("evidence/member_discovery_failure.png")
    input("\nBrowser left open for inspection. Press Enter to close...")
    raise
finally:
    surface.close()
