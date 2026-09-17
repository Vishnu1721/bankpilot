"""Explicit test-only failures at the browser adapter boundary."""

from src.surface.browser import BrowserSurface


class FaultInjectionSurface(BrowserSurface):
    def __init__(self, target_name, failure_mode="once", *, headless=False):
        super().__init__(headless=headless)
        if failure_mode not in {"once", "persistent"}:
            raise ValueError("Unknown failure mode.")
        self.failure_target = target_name
        self.failure_mode = failure_mode
        self.injected_failures = 0

    def find_target(self, target):
        if target.name == self.failure_target and (
            self.failure_mode == "persistent" or self.injected_failures == 0
        ):
            self.injected_failures += 1
            message = (
                "Simulated temporary UI condition."
                if self.failure_mode == "once"
                else "Search target remained unavailable."
            )
            raise RuntimeError(message)
        return super().find_target(target)
