import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from src.agent.models import ActionType


class SafetyViolation(Exception):
    """Raised when BankPilot blocks an operation outside explicit policy."""


@dataclass(frozen=True)
class RoutePolicy:
    path_pattern: str
    actions: frozenset[ActionType]
    click_targets: frozenset[str] = field(default_factory=frozenset)


COMMON = {ActionType.READ, ActionType.WAIT, ActionType.FINISH, ActionType.ESCALATE}
DEFAULT_ROUTE_POLICIES = (
    RoutePolicy(r"/", frozenset(COMMON | {ActionType.CLICK}), frozenset({"Member Lookup", "Balance Lookup", "Create Sub-account", "Deposit"})),
    RoutePolicy(r"/member-search", frozenset(COMMON | {ActionType.TYPE, ActionType.CLICK}), frozenset({"Search Member", "Operations"})),
    RoutePolicy(r"/member", frozenset(COMMON | {ActionType.CLICK}), frozenset({"Open New Sub-account", "Return to Member Search"})),
    RoutePolicy(r"/verify/[0-9]+", frozenset(COMMON)),
    RoutePolicy(r"/balance-lookup", frozenset(COMMON | {ActionType.TYPE, ActionType.SELECT, ActionType.CLICK}), frozenset({"View Balance", "Operations"})),
    RoutePolicy(r"/balance", frozenset(COMMON)),
    RoutePolicy(r"/sub-account(?:/[0-9]+)?", frozenset(COMMON | {ActionType.TYPE, ActionType.SELECT, ActionType.CLICK}), frozenset({"Continue to Review", "Operations"})),
    RoutePolicy(r"/sub-account/review", frozenset(COMMON)),
    RoutePolicy(r"/deposit", frozenset(COMMON | {ActionType.TYPE, ActionType.SELECT, ActionType.CLICK}), frozenset({"Continue to Deposit Review", "Operations"})),
    RoutePolicy(r"/deposit/review", frozenset(COMMON)),
)


class SafetyPolicy:
    def __init__(self, allowed_hosts=None, route_policies=None):
        self.allowed_hosts = set(allowed_hosts or {"127.0.0.1", "localhost"})
        self.route_policies = tuple(route_policies or DEFAULT_ROUTE_POLICIES)

    def check_url(self, url):
        parsed = urlparse(url)
        if parsed.hostname not in self.allowed_hosts:
            raise SafetyViolation(f"Navigation blocked. Host '{parsed.hostname}' is not allowed.")
        path = parsed.path or "/"
        if self._route_for(path) is None:
            raise SafetyViolation(f"Navigation blocked. Route '{path}' is not allowed.")

    def check_action(self, action, observation):
        route = self._require_route(observation.url)
        if action.action not in route.actions:
            raise SafetyViolation(f"Action '{action.action.value}' is not allowed on this route.")
        if action.action not in {ActionType.CLICK, ActionType.TYPE, ActionType.SELECT}:
            return
        if action.element_id is None:
            raise SafetyViolation(f"{action.action.value.title()} action has no target.")
        target = self._find_element(action.element_id, observation)
        if action.action == ActionType.CLICK and target.name not in route.click_targets:
            path = urlparse(observation.url).path or "/"
            raise SafetyViolation(f"Click target '{target.name}' is not approved on route '{path}'.")

    def check_replay_target(self, action, target, current_url):
        if action == "extract":
            self._require_route(current_url)
            return
        try:
            action_type = ActionType(action)
        except ValueError as error:
            raise SafetyViolation(f"Replay action '{action}' is not allowed.") from error
        route = self._require_route(current_url)
        if action_type not in route.actions:
            raise SafetyViolation(f"Replay action '{action}' is not allowed on this route.")
        if action_type == ActionType.CLICK:
            if target is None or target.name not in route.click_targets:
                name = target.name if target else None
                raise SafetyViolation(f"Replay click target '{name}' is not approved on this route.")

    def _require_route(self, url):
        self.check_url(url)
        return self._route_for(urlparse(url).path or "/")

    def _route_for(self, path):
        matches = [policy for policy in self.route_policies if re.fullmatch(policy.path_pattern, path)]
        return max(matches, key=lambda item: len(item.path_pattern)) if matches else None

    @staticmethod
    def _find_element(element_id, observation):
        for element in observation.elements:
            if element.element_id == element_id:
                return element
        raise SafetyViolation(f"Target '{element_id}' does not exist in the observation.")
