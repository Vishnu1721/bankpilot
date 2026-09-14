from src.capability.replay import ReplayEngine
from src.surface.browser import BrowserSurface


CAPABILITY_PATH = (
    "evidence/"
    "example_capability.json"
)


class HardFailureReplayEngine(
    ReplayEngine
):

    def _find_target(
        self,
        target
    ):
        if target.name == "Search Member":
            raise RuntimeError(
                "Search target remained "
                "unavailable."
            )

        return super()._find_target(
            target
        )


surface = BrowserSurface(
    headless=False
)

try:
    surface.start()

    engine = HardFailureReplayEngine(
        surface,
        max_retries=2,
        retry_delay_ms=500,
        log_path=(
            "evidence/"
            "replay_failure.jsonl"
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

    assert result.status.value == "failure", result
    assert result.code == "STEP_EXECUTION_FAILED", result
    assert result.failed_step == "step_3", result

    print(
        "\nHARD FAILURE RESULT"
    )
    print(
        "==================="
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )

    input(
        "\nPress Enter to close..."
    )

finally:
    surface.close()
