from src.capability.replay import ReplayEngine
from src.surface.browser import BrowserSurface


CAPABILITY_PATH = (
    "artifacts/"
    "lookup_savings_balance.json"
)


surface = BrowserSurface(
    headless=False
)

try:
    surface.start()

    engine = ReplayEngine(
        surface,
        log_path=(
            "evidence/"
            "replay_success.jsonl"
        )
    )

    capability = (
        engine.load_capability(
            CAPABILITY_PATH
        )
    )

    result = engine.run(
        capability,
        inputs={
            "member_id": "10024"
        }
    )

    print(
        "\nFINAL REPLAY RESULT"
    )
    print(
        "==================="
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )

    surface.screenshot(
        "evidence/replay_final.png"
    )

    input(
        "\nPress Enter to close..."
    )

finally:
    surface.close()