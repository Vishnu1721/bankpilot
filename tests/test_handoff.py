from src.handoff.replay import (
    HandoffReplayEngine
)

from src.surface.browser import (
    BrowserSurface
)


CAPABILITY_PATH = (
    "artifacts/"
    "lookup_savings_balance.json"
)


surface = BrowserSurface(
    headless=False
)


try:
    surface.start()

    engine = (
        HandoffReplayEngine(
            surface
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
            "member_id": "10025"
        }
    )

    print(
        "\nHANDOFF REPLAY RESULT"
    )

    print(
        "====================="
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )

    print(
        "\nHuman handoffs: "
        f"{engine.handoff_count}"
    )

    surface.screenshot(
        "evidence/"
        "handoff_final.png"
    )

    input(
        "\nPress Enter to close..."
    )

finally:
    surface.close()