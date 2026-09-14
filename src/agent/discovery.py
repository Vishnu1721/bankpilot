from src.agent.budget import DiscoveryBudget, DiscoveryBudgetExceeded
from src.agent.llm import LLMClient
from src.agent.models import ActionType
from src.capability.recorder import CapabilityRecorder
from src.observability.logger import EventLogger
from src.safety.observation import UntrustedObservationGuard
from src.safety.policy import SafetyPolicy


class DiscoveryAgent:

    def __init__(
        self,
        surface,
        max_steps=10,
        safety_policy=None,
        log_path="evidence/discovery_log.jsonl",
        budget=None,
        observation_guard=None,
        llm=None,
    ):
        self.surface = surface
        self.budget_config = budget or DiscoveryBudget(max_steps=max_steps)
        self.llm = llm or LLMClient()
        self.recorder = CapabilityRecorder()
        self.safety = safety_policy or SafetyPolicy()
        self.observation_guard = observation_guard or UntrustedObservationGuard(
            max_text_chars=self.budget_config.max_observation_chars
        )
        self.logger = EventLogger(log_path)

    def run(self, goal, artifact_path=None, parameters=None):
        print("\nBANKPILOT DISCOVERY")
        print("===================")
        print(f"\nGoal: {goal}")

        parameters = parameters or {}
        self.recorder.set_parameters(parameters)
        budget = DiscoveryBudget(
            max_steps=self.budget_config.max_steps,
            max_llm_calls=self.budget_config.max_llm_calls,
            max_elapsed_seconds=self.budget_config.max_elapsed_seconds,
            max_observation_chars=self.budget_config.max_observation_chars,
            max_same_state=self.budget_config.max_same_state,
        )

        start_url = self.surface.page.url if hasattr(self.surface, "page") else ""
        self.safety.check_url(start_url)
        self.logger.log(
            "discovery_started",
            start_url=start_url,
            parameter_names=list(parameters.keys()),
            budget={
                "max_steps": budget.max_steps,
                "max_llm_calls": budget.max_llm_calls,
                "max_elapsed_seconds": budget.max_elapsed_seconds,
                "max_observation_chars": budget.max_observation_chars,
                "max_same_state": budget.max_same_state,
            },
        )

        try:
            for step_number in range(1, budget.max_steps + 1):
                budget.check_before_step(step_number)
                print(f"\n--- Step {step_number} ---")

                raw_observation = self.surface.observe()
                observation = self.observation_guard.sanitize(raw_observation)
                self.safety.check_url(observation.url)
                budget.record_observation(observation)

                print(f"Page: {observation.title}")
                print(f"URL: {observation.url}")
                self.logger.log(
                    "observation",
                    step=step_number,
                    title=observation.title,
                    url=observation.url,
                    trust=observation.trust,
                    fingerprint=observation.fingerprint(),
                )

                budget.record_llm_call()
                action = self.llm.decide(goal, observation)
                print(f"Decision: {action.action.value}")
                print(f"Reason: {action.reasoning}")
                if action.element_id:
                    target = next(
                        element for element in observation.elements
                        if element.element_id == action.element_id
                    )
                    print(f"Target: {target.name} [{target.selector}]")

                self.logger.log(
                    "agent_decision",
                    step=step_number,
                    action=action.action.value,
                    element_id=action.element_id,
                )
                self.safety.check_action(action, observation)

                if action.action == ActionType.FINISH:
                    capability = self.recorder.build_capability(
                        start_url,
                        goal=goal,
                        result=action.result,
                    )
                    if artifact_path:
                        self.recorder.save(capability, artifact_path)
                    self.logger.log(
                        "discovery_completed",
                        status="success",
                        capability_id=capability.capability_id,
                        steps_used=step_number,
                        llm_calls=budget.llm_calls,
                    )
                    return action.result

                if action.action == ActionType.ESCALATE:
                    self.logger.log("discovery_escalated", reason=action.reasoning)
                    return {"status": "escalated", "reason": action.reasoning}

                if action.action == ActionType.WAIT:
                    self.surface.wait(1000)
                    continue

                if action.action == ActionType.READ:
                    continue

                self.recorder.record_action(action, observation)
                self.surface.execute(action, observation)
                current_url = (
                    self.surface.page.url
                    if hasattr(self.surface, "page") and self.surface.page
                    else observation.url
                )
                print(f"After action URL: {current_url}")
                self.logger.log(
                    "action_executed",
                    step=step_number,
                    action=action.action.value,
                )

            raise DiscoveryBudgetExceeded(
                f"Discovery budget exceeded: max_steps ({budget.max_steps})."
            )
        except Exception as error:
            self.logger.log(
                "discovery_failed",
                reason=type(error).__name__,
                message=str(error),
            )
            raise
