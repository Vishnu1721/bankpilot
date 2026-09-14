from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.surface.browser import BrowserSurface


GOAL = (
    "Look up member 10023, prepare a Holiday Savings sub-account "
    "named Vacation, and reach the confirmation review screen. "
    "Do not confirm or open the account."
)
START_URL = "http://127.0.0.1:5001"
ARTIFACT_PATH = "artifacts/prepare_new_subaccount.json"


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
        log_path="evidence/subaccount_discovery.jsonl",
    )
    result = agent.run(
        goal=GOAL,
        artifact_path=ARTIFACT_PATH,
        parameters={
            "member_id": "10023",
            "account_type": "Holiday Savings",
            "nickname": "Vacation",
        },
    )
    print(result)
    surface.screenshot("evidence/subaccount_review.png")
    input("\nPress Enter to close...")
finally:
    surface.close()
