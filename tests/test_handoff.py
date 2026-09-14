from src.handoff.replay import (
    HandoffReplayEngine
)

from src.surface.browser import (
    BrowserSurface
)


CAPABILITY_PATH = (
    "evidence/"
    "example_capability.json"
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

    assert result.status.value == "success", result
    assert engine.handoff_count == 1, "Expected exactly one human handoff."
    assert result.outputs == {"savings_balance": "$3675.20"}, result

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
