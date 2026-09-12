from src.capability.replay import ReplayEngine
from src.surface.browser import BrowserSurface


CAPABILITY_PATH = (
    "artifacts/"
    "lookup_savings_balance.json"
)


class RecoverableReplayEngine(
    ReplayEngine
):

    def __init__(
        self,
        surface
    ):
        super().__init__(
            surface,
            max_retries=2,
            retry_delay_ms=500,
            log_path=(
                "evidence/"
                "replay_recovered.jsonl"
            )
        )

        self.simulated_failure = False

    def _find_target(
        self,
        target
    ):
        if (
            target.name == "Search"
            and not self.simulated_failure
        ):
            self.simulated_failure = True

            raise RuntimeError(
                "Simulated temporary "
                "UI condition."
            )

        return super()._find_target(
            target
        )


surface = BrowserSurface(
    headless=False
)

try:
    surface.start()

    engine = RecoverableReplayEngine(
        surface
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
        "\nRECOVERABLE REPLAY RESULT"
    )
    print(
        "========================="
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