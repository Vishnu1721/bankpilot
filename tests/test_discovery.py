from src.agent.discovery import DiscoveryAgent
from src.surface.browser import BrowserSurface


GOAL = (
    "Look up member 10023 and return "
    "their current savings balance."
)

START_URL = "http://127.0.0.1:5001"

ARTIFACT_PATH = (
    "artifacts/"
    "lookup_savings_balance.json"
)

DISCOVERY_LOG_PATH = (
    "evidence/"
    "discovery_log.jsonl"
)


surface = BrowserSurface(
    headless=False
)

try:
    surface.start()

    surface.navigate(
        START_URL
    )

    agent = DiscoveryAgent(
        surface=surface,
        max_steps=6,
        log_path=DISCOVERY_LOG_PATH
    )

    result = agent.run(
        goal=GOAL,
        artifact_path=ARTIFACT_PATH,

        # This tells the recorder that the
        # runtime value 10023 corresponds
        # to the reusable member_id parameter.
        parameters={
            "member_id": "10023"
        }
    )

    print(
        "\nFINAL RESULT"
    )

    print(
        "============"
    )

    print(result)

    surface.screenshot(
        "evidence/"
        "discovery_final.png"
    )

    input(
        "\nPress Enter to close..."
    )

finally:
    surface.close()