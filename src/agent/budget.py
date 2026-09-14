from dataclasses import dataclass, field
from time import monotonic


class DiscoveryBudgetExceeded(RuntimeError):
    pass


@dataclass
class DiscoveryBudget:
    max_steps: int = 10
    max_llm_calls: int = 10
    max_elapsed_seconds: float = 120.0
    max_observation_chars: int = 8000
    max_same_state: int = 3
    started_at: float = field(default_factory=monotonic)
    llm_calls: int = 0
    last_fingerprint: str | None = None
    same_state_count: int = 0

    def check_before_step(self, step_number):
        if step_number > self.max_steps:
            self._fail("max_steps")
        if monotonic() - self.started_at > self.max_elapsed_seconds:
            self._fail("max_elapsed_seconds")

    def record_observation(self, observation):
        size = len(observation.text) + sum(
            len(element.name) + len(element.value or "")
            for element in observation.elements
        )
        if size > self.max_observation_chars:
            self._fail("max_observation_chars")

        fingerprint = observation.fingerprint()
        if fingerprint == self.last_fingerprint:
            self.same_state_count += 1
        else:
            self.last_fingerprint = fingerprint
            self.same_state_count = 1

        if self.same_state_count > self.max_same_state:
            self._fail("max_same_state")

    def record_llm_call(self):
        self.llm_calls += 1
        if self.llm_calls > self.max_llm_calls:
            self._fail("max_llm_calls")

    @staticmethod
    def _fail(limit):
        raise DiscoveryBudgetExceeded(f"Discovery budget exceeded: {limit}.")
