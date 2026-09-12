from src.agent.llm import LLMClient
from src.agent.models import ActionType
from src.capability.recorder import CapabilityRecorder
from src.observability.logger import EventLogger
from src.safety.policy import SafetyPolicy


class DiscoveryAgent:

    def __init__(
        self,
        surface,
        max_steps=10,
        safety_policy=None,
        log_path="evidence/discovery_log.jsonl"
    ):
        self.surface = surface
        self.max_steps = max_steps
        self.llm = LLMClient()
        self.recorder = CapabilityRecorder()

        self.safety = (
            safety_policy
            or SafetyPolicy()
        )

        self.logger = EventLogger(
            log_path
        )

    def run(
        self,
        goal,
        artifact_path=None,
        parameters=None
    ):
        print("\nBANKPILOT DISCOVERY")
        print("===================")
        print(f"\nGoal: {goal}")

        parameters = parameters or {}

        self.recorder.set_parameters(
            parameters
        )

        start_url = self.surface.page.url

        self.safety.check_url(
            start_url
        )

        self.logger.log(
            "discovery_started",
            start_url=start_url,
            parameter_names=list(
                parameters.keys()
            )
        )

        for step_number in range(
            1,
            self.max_steps + 1
        ):
            print(
                f"\n--- Step {step_number} ---"
            )

            observation = (
                self.surface.observe()
            )

            self.safety.check_url(
                observation.url
            )

            print(
                f"Page: {observation.title}"
            )

            self.logger.log(
                "observation",
                step=step_number,
                title=observation.title,
                url=observation.url
            )

            action = self.llm.decide(
                goal,
                observation
            )

            print(
                f"Decision: "
                f"{action.action.value}"
            )

            print(
                f"Reason: "
                f"{action.reasoning}"
            )

            if action.element_id:
                print(
                    f"Element: "
                    f"{action.element_id}"
                )

            if action.value:
                print(
                    f"Value: "
                    f"{action.value}"
                )

            self.logger.log(
                "agent_decision",
                step=step_number,
                action=action.action.value,
                element_id=action.element_id
            )

            self.safety.check_action(
                action,
                observation
            )

            if (
                action.action
                == ActionType.FINISH
            ):
                print("\nGOAL COMPLETED")
                print(
                    f"Result: {action.result}"
                )

                capability = (
                    self.recorder
                    .build_capability(
                        start_url
                    )
                )

                if artifact_path:
                    self.recorder.save(
                        capability,
                        artifact_path
                    )

                    print(
                        "\nCapability saved to: "
                        f"{artifact_path}"
                    )

                self.logger.log(
                    "discovery_completed",
                    status="success",
                    capability_id=(
                        capability.capability_id
                    )
                )

                return action.result

            if (
                action.action
                == ActionType.ESCALATE
            ):
                self.logger.log(
                    "discovery_escalated"
                )

                print(
                    "\nHUMAN HELP REQUIRED"
                )

                return {
                    "status": "escalated"
                }

            if (
                action.action
                == ActionType.WAIT
            ):
                self.surface.page.wait_for_timeout(
                    1000
                )

                continue

            if (
                action.action
                == ActionType.READ
            ):
                continue

            self.recorder.record_action(
                action,
                observation
            )

            self.surface.execute(
                action,
                observation
            )

            self.logger.log(
                "action_executed",
                step=step_number,
                action=action.action.value
            )

        self.logger.log(
            "discovery_failed",
            reason="max_steps_exceeded"
        )

        raise RuntimeError(
            "Discovery exceeded the "
            f"maximum of {self.max_steps} steps."
        )