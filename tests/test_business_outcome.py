from src.capability.replay import ReplayEngine
from src.surface.browser import BrowserSurface


CAPABILITY_PATH = (
    "evidence/"
    "example_capability.json"
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
            "replay_business_outcome.jsonl"
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
            "member_id": "99999"
        }
    )

    assert result.status.value == "business_outcome", result
    assert result.code == "MEMBER_NOT_FOUND", result

    print(
        "\nBUSINESS OUTCOME RESULT"
    )
    print(
        "======================="
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )

    surface.screenshot(
        "evidence/"
        "business_outcome.png"
    )

    input(
        "\nPress Enter to close..."
    )

finally:
    surface.close()
