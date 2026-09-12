from src.capability.replay import ReplayEngine

from src.handoff.manager import (
    HumanHandoffManager
)


class HandoffReplayEngine(
    ReplayEngine
):

    def __init__(
        self,
        surface,
        safety_policy=None,
        max_retries=2,
        retry_delay_ms=500,
        log_path=(
            "evidence/"
            "handoff_log.jsonl"
        )
    ):
        super().__init__(
            surface=surface,
            safety_policy=safety_policy,
            max_retries=max_retries,
            retry_delay_ms=retry_delay_ms,
            log_path=log_path
        )

        self.handoff = (
            HumanHandoffManager(
                surface
            )
        )

        self.handoff_count = 0

    def _perform_handoff(
        self,
        reason
    ):
        self.handoff_count += 1

        self.logger.log(
            "handoff_started",
            reason=reason
        )

        self.handoff.handoff(
            reason=reason
        )

        self.logger.log(
            "handoff_completed",
            handoff_number=(
                self.handoff_count
            )
        )

    def _detect_business_outcome(
        self
    ):
        if (
            self.handoff
            .requires_handoff()
        ):
            self._perform_handoff(
                reason=(
                    "LegacyBank requires "
                    "manual member verification."
                )
            )

        return (
            super()
            ._detect_business_outcome()
        )

    def _extract_value(
        self,
        label
    ):
        if (
            self.handoff
            .requires_handoff()
        ):
            self._perform_handoff(
                reason=(
                    "Account information is "
                    "blocked pending manual "
                    "verification."
                )
            )

        return super()._extract_value(
            label
        )