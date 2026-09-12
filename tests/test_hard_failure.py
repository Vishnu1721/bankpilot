from src.capability.replay import ReplayEngine
from src.surface.browser import BrowserSurface


CAPABILITY_PATH = (
    "artifacts/"
    "lookup_savings_balance.json"
)


class HardFailureReplayEngine(
    ReplayEngine
):

    def _find_target(
        self,
        target
    ):
        if target.name == "Search":
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