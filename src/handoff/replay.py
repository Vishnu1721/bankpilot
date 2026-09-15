from src.capability.replay import ReplayEngine
from src.handoff.manager import HumanHandoffManager


class HandoffReplayEngine(ReplayEngine):
    """Replay engine with generalized same-session operator takeover."""

    def __init__(
        self,
        surface,
        safety_policy=None,
        max_retries=2,
        retry_delay_ms=500,
        log_path="evidence/handoff_log.jsonl",
    ):
        super().__init__(
            surface=surface,
            safety_policy=safety_policy,
            max_retries=max_retries,
            retry_delay_ms=retry_delay_ms,
            log_path=log_path,
            handoff_manager=HumanHandoffManager(surface),
        )
