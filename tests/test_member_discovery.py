from src.agent.discovery import DiscoveryAgent
from src.surface.browser import BrowserSurface


surface = BrowserSurface(headless=False)
try:
    surface.start()
    surface.navigate("http://127.0.0.1:5001")
    result = DiscoveryAgent(
        surface, max_steps=7, log_path="evidence/member_discovery.jsonl"
    ).run(
        goal="From the operations dashboard, perform a member lookup for member 10023 and return the member profile.",
        artifact_path="artifacts/lookup_member.json",
        parameters={"member_id": "10023"},
    )
    print(result)
    surface.screenshot("evidence/member_details.png")
    input("\nPress Enter to close...")
finally:
    surface.close()
