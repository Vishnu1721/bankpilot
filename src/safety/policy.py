from urllib.parse import urlparse

from src.agent.models import ActionType


class SafetyViolation(Exception):
    """Raised when BankPilot blocks an unsafe operation."""
    pass


class SafetyPolicy:

    def __init__(self, allowed_hosts=None, allowed_actions=None):
        self.allowed_hosts = set(allowed_hosts or {"127.0.0.1", "localhost"})
        self.allowed_actions = set(
            allowed_actions
            or {
                ActionType.TYPE,
                ActionType.SELECT,
                ActionType.CLICK,
                ActionType.READ,
                ActionType.WAIT,
                ActionType.FINISH,
                ActionType.ESCALATE,
            }
        )
        # Clicking into a draft/review flow is permitted. The final commitment
        # control remains blocked and requires explicit human approval.
        self.risky_keywords = {
            "delete",
            "remove",
            "transfer",
            "withdraw",
            "send money",
            "create account",
            "close account",
            "submit payment",
            "approve payment",
            "confirm payment",
            "confirm & open",
            "post deposit",
            "open account now",
        }

    def check_url(self, url):
        host = urlparse(url).hostname
        if host not in self.allowed_hosts:
            raise SafetyViolation(
                f"Navigation blocked. Host '{host}' is not allowed."
            )

    def check_action(self, action, observation):
        if action.action not in self.allowed_actions:
            raise SafetyViolation(f"Action '{action.action.value}' is not allowed.")

        if action.action not in {ActionType.CLICK, ActionType.TYPE, ActionType.SELECT}:
            return
        if action.element_id is None:
            raise SafetyViolation(f"{action.action.value.title()} action has no target.")

        target = self._find_element(action.element_id, observation)
        if action.action == ActionType.CLICK:
            target_text = (target.name or "").lower()
            for keyword in self.risky_keywords:
                if keyword in target_text:
                    raise SafetyViolation(f"Risky action blocked: '{target.name}'.")

    def check_replay_target(self, action, target):
        if action not in {"type", "select", "click", "extract", "wait"}:
            raise SafetyViolation(f"Replay action '{action}' is not allowed.")
        if action != "click":
            return
        if target is None:
            raise SafetyViolation("Replay click has no target.")

        target_text = (target.name or "").lower()
        for keyword in self.risky_keywords:
            if keyword in target_text:
                raise SafetyViolation(f"Risky replay action blocked: '{target.name}'.")

    @staticmethod
    def _find_element(element_id, observation):
        for element in observation.elements:
            if element.element_id == element_id:
                return element
        raise SafetyViolation(f"Target '{element_id}' does not exist in the observation.")
