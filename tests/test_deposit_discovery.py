from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.surface.browser import BrowserSurface


GOAL = (
    "From the operations dashboard, prepare a $200 deposit to the Savings "
    "account for member 10024 with memo Cash deposit. Reach Deposit Review "
    "and do not post the deposit."
)
START_URL = "http://127.0.0.1:5001"
ARTIFACT_PATH = "artifacts/prepare_deposit.json"

surface = BrowserSurface(headless=False)

try:
    surface.start()
    surface.navigate(START_URL)
    agent = DiscoveryAgent(
        surface=surface,
        budget=DiscoveryBudget(
            max_steps=9,
            max_llm_calls=9,
            max_elapsed_seconds=90,
            max_observation_chars=8000,
            max_same_state=2,
        ),
        log_path="evidence/deposit_discovery.jsonl",
    )
    result = agent.run(
        goal=GOAL,
        artifact_path=ARTIFACT_PATH,
        parameters={
            "member_id": "10024",
            "account_type": "Savings",
            "amount": "200",
            "memo": "Cash deposit",
        },
    )
    print(result)
    surface.screenshot("evidence/deposit_review.png")
    input("\nPress Enter to close...")
except Exception as error:
    print(f"\nDISCOVERY FAILED: {error}")
    surface.screenshot("evidence/live_discovery_failure.png")
    input("\nBrowser left open for inspection. Press Enter to close...")
    raise
finally:
    surface.close()
