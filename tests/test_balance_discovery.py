from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.surface.browser import BrowserSurface

GOAL = (
    "From the operations dashboard, use Balance Lookup to return the current "
    "Savings balance for member 10024."
)
surface = BrowserSurface(headless=False)

try:
    surface.start()
    surface.navigate("http://127.0.0.1:5001")
    result = DiscoveryAgent(
        surface=surface,
        budget=DiscoveryBudget(max_steps=7, max_llm_calls=7, max_elapsed_seconds=60),
        log_path="evidence/balance_discovery.jsonl",
    ).run(
        goal=GOAL,
        artifact_path="artifacts/lookup_balance.json",
        parameters={"member_id": "10024", "account_type": "Savings"},
    )
    print(result)
    surface.screenshot("evidence/balance_result.png")
    input("\nPress Enter to close...")
except Exception as error:
    print(f"\nDISCOVERY FAILED: {error}")
    surface.screenshot("evidence/balance_discovery_failure.png")
    input("\nBrowser left open for inspection. Press Enter to close...")
    raise
finally:
    surface.close()
