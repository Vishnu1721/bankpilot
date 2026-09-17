from src.capability.replay import ReplayEngine
from tests.fault_surface import FaultInjectionSurface


CAPABILITY_PATH = (
    "evidence/"
    "example_capability.json"
)


surface = FaultInjectionSurface(
    "Search Member", failure_mode="once", headless=False
)

try:
    surface.start()

    engine = ReplayEngine(
        surface,
        max_retries=2,
        retry_delay_ms=500,
        log_path="evidence/replay_recovered.jsonl",
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

    assert result.status.value == "success", result
    assert result.recovered_steps == ["step_3"], result
    assert result.outputs == {"savings_balance": "$2150.75"}, result

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
