from src.agent.discovery import DiscoveryAgent
from src.surface.browser import BrowserSurface


surface = BrowserSurface(headless=False)
try:
    surface.start()
    surface.navigate("http://127.0.0.1:5001")
    result = DiscoveryAgent(
        surface, max_steps=8, log_path="evidence/balance_discovery.jsonl"
    ).run(
        goal="From the operations dashboard, perform a balance lookup for member 10024 Savings and return the current balance.",
        artifact_path="artifacts/lookup_balance.json",
        parameters={"member_id": "10024", "account_type": "Savings"},
    )
    print(result)
    surface.screenshot("evidence/balance_result.png")
    input("\nPress Enter to close...")
finally:
    surface.close()
