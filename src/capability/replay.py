import json
import re
from src.handoff.manager import HandoffCancelled
from pathlib import Path

from src.capability.models import (
    Capability,
    DataType,
    StepType
)

from src.capability.results import (
    ReplayResult,
    ReplayStatus
)

from src.observability.logger import (
    EventLogger
)

from src.safety.policy import (
    SafetyPolicy,
    SafetyViolation,
)


class OutputContractError(RuntimeError):
    """Raised when replay did not produce every declared capability output."""


class IdentityMismatchError(RuntimeError):
    """Raised when returned customer data belongs to another member."""


class RuntimeConditionError(RuntimeError):
    """A classified runtime condition with an explicit retry policy."""

    def __init__(self, code, message, retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ReplayEngine:

    def __init__(
        self,
        surface,
        safety_policy=None,
        max_retries=2,
        retry_delay_ms=500,
        log_path="evidence/replay_log.jsonl",
        handoff_manager=None,
    ):
        self.surface = surface

        self.safety = (
            safety_policy
            or SafetyPolicy()
        )

        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms

        self.recovered_steps = []
        self.active_capability_id = None
        self.current_step_id = None
        self.handoff_manager = handoff_manager
        self.handoff_count = 0
        self._last_click_navigated = False

        self.logger = EventLogger(
            log_path
        )

    def load_capability(
        self,
        path
    ):
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return Capability.model_validate(
            data
        )

    def run(
        self,
        capability,
        inputs
    ):
        print("\nBANKPILOT REPLAY")
        print("================")

        print(
            f"\nCapability: "
            f"{capability.name}"
        )

        self.recovered_steps = []
        self.active_capability_id = capability.capability_id
        self.current_step_id = None

        self.logger.log(
            "replay_started",
            capability_id=(
                capability.capability_id
            ),
            capability_name=(
                capability.name
            )
        )

        try:
            self._validate_inputs(
                capability,
                inputs
            )

            business_result = self._validate_business_inputs(capability, inputs)
            if business_result:
                self._log_outcome(business_result)
                return business_result

            self.safety.check_url(
                capability.start_url
            )

            self.surface.navigate(
                capability.start_url
            )

            outputs = {}

            for step in capability.steps:
                self.current_step_id = step.step_id

                print(
                    f"\n--- {step.step_id} ---"
                )

                print(
                    f"Action: "
                    f"{step.action.value}"
                )

                self.logger.log(
                    "step_started",
                    step_id=step.step_id,
                    action=step.action.value,
                    target=(
                        step.target.name
                        if step.target
                        else None
                    )
                )

                self.safety.check_url(
                    self.surface.current_url()
                )

                business_result = (
                    self._detect_business_outcome()
                )

                if business_result:
                    self._log_outcome(business_result)
                    return business_result

                try:
                    recovered = (
                        self._execute_step_with_retry(
                            step,
                            capability,
                            inputs,
                            outputs
                        )
                    )

                    if recovered:
                        self.recovered_steps.append(
                            step.step_id
                        )

                        self.logger.log(
                            "step_recovered",
                            step_id=step.step_id
                        )

                    self.logger.log(
                        "step_completed",
                        step_id=step.step_id
                    )

                except IdentityMismatchError as error:
                    result = self._identity_failure_result(error)
                    self.logger.log(
                        "replay_failed",
                        code=result.code,
                        failed_step=step.step_id,
                        message=result.message,
                        evidence_path=result.evidence_path,
                    )
                    return result
                except RuntimeConditionError as error:
                    result = self._failure_result(step, error)
                    self.logger.log(
                        "replay_failed",
                        code=result.code,
                        failed_step=result.failed_step,
                        message=result.message,
                        evidence_path=result.evidence_path,
                    )
                    return result
                except Exception as error:
                    if self.handoff_manager is not None:
                        self._perform_handoff(
                            f"Automation was blocked at {step.step_id}: {error}"
                        )
                        if step.action == StepType.EXTRACT:
                            try:
                                self._execute_step_with_retry(
                                    step,
                                    capability,
                                    inputs,
                                    outputs,
                                )
                            except Exception as retry_error:
                                result = self._failure_result(step, retry_error)
                                self.logger.log(
                                    "replay_failed",
                                    code=result.code,
                                    failed_step=result.failed_step,
                                    message=result.message,
                                    evidence_path=result.evidence_path,
                                )
                                return result
                        self.recovered_steps.append(step.step_id)
                        self.logger.log(
                            "step_completed",
                            step_id=step.step_id,
                            completed_by=(
                                "automation_after_handoff"
                                if step.action == StepType.EXTRACT
                                else "human"
                            ),
                        )
                        continue
                    result = self._failure_result(
                        step,
                        error
                    )

                    self.logger.log(
                        "replay_failed",
                        code=result.code,
                        failed_step=(
                            result.failed_step
                        ),
                        message=result.message,
                        evidence_path=(
                            result.evidence_path
                        )
                    )

                    return result

                business_result = (
                    self._detect_business_outcome(
                        include_validation=(
                            step.action == StepType.CLICK
                            and not self._last_click_navigated
                        )
                    )
                )

                if business_result:
                    self._log_outcome(business_result)
                    return business_result

            try:
                self._validate_outputs(
                    capability,
                    outputs,
                )
                self._check_success(
                    capability
                )

            except OutputContractError as error:
                result = self._output_contract_failure_result(error)
                self.logger.log(
                    "replay_failed",
                    code=result.code,
                    message=result.message,
                    evidence_path=result.evidence_path,
                )
                return result
            except Exception as error:
                result = (
                    self._final_failure_result(
                        error
                    )
                )

                self.logger.log(
                    "replay_failed",
                    code=result.code,
                    message=result.message,
                    evidence_path=(
                        result.evidence_path
                    )
                )

                return result

            print(
                "\nREPLAY COMPLETED"
            )

            result = ReplayResult(
                status=ReplayStatus.SUCCESS,
                outputs=outputs,
                message=(
                    "Capability replay "
                    "completed successfully."
                ),
                recovered_steps=(
                    self.recovered_steps
                )
            )

            self.logger.log(
                "replay_completed",
                status="success",
                outputs=outputs,
                recovered_steps=(
                    self.recovered_steps
                )
            )

            return result

        except Exception as error:
            evidence_path = (
                self._capture_failure_evidence(
                    "replay_failure"
                )
            )

            result = ReplayResult(
                status=ReplayStatus.FAILURE,
                code="REPLAY_FAILURE",
                message=str(error),
                expected=(
                    "Capability should complete "
                    "successfully."
                ),
                observed=(
                    self._current_page_summary()
                ),
                recovered_steps=(
                    self.recovered_steps
                ),
                evidence_path=evidence_path
            )

            self.logger.log(
                "replay_failed",
                code=result.code,
                message=result.message,
                evidence_path=evidence_path
            )

            return result

    def _execute_step_with_retry(
        self,
        step,
        capability,
        inputs,
        outputs
    ):
        last_error = None

        for attempt in range(
            1,
            self.max_retries + 2
        ):
            try:
                self._raise_transient_application_state()
                self._execute_step(
                    step,
                    capability,
                    inputs,
                    outputs
                )
                self._raise_transient_application_state()

                if attempt > 1:
                    print(
                        "Recovered after "
                        f"{attempt - 1} retry(s)."
                    )

                    return True

                return False

            except (SafetyViolation, IdentityMismatchError):
                raise
            except RuntimeConditionError as error:
                if not error.retryable:
                    raise
                last_error = error
            except Exception as error:
                last_error = error

            if attempt > self.max_retries:
                break

            print(
                "Recoverable condition "
                f"at {step.step_id}: "
                f"{last_error}"
            )
            print(f"Retrying ({attempt}/{self.max_retries})...")
            self.logger.log(
                "step_retry",
                step_id=step.step_id,
                attempt=attempt,
                error=str(last_error)
            )
            self.surface.wait(self.retry_delay_ms)

        raise last_error

    def _execute_step(
        self,
        step,
        capability,
        inputs,
        outputs
    ):
        self.safety.check_replay_target(
            step.action.value,
            step.target,
            self.surface.current_url(),
        )

        if (
            step.action
            == StepType.TYPE
        ):
            value = self._resolve_value(
                step.value,
                inputs
            )

            print(
                f"Value: {value}"
            )

            self.surface.fill_target(step.target, value)

        elif (
            step.action
            == StepType.SELECT
        ):
            value = self._resolve_value(
                step.value,
                inputs
            )

            self.surface.select_target(step.target, value)

        elif (
            step.action
            == StepType.CLICK
        ):
            before_url = self.surface.current_url()
            destination = self.surface.target_destination(step.target)
            if destination:
                self.safety.check_url(destination)
            self.surface.click_target(step.target)
            self._last_click_navigated = self.surface.current_url() != before_url

            self.safety.check_url(
                self.surface.current_url()
            )


        elif (
            step.action
            == StepType.WAIT
        ):
            self.surface.wait(
                1000
            )

        elif (
            step.action
            == StepType.EXTRACT
        ):
            self._verify_requested_identity(inputs)
            extracted = self._extract_value(
                step.value
            )

            output_name = step.output_name
            if output_name is None:
                raise ValueError(f"Extract step {step.step_id} has no output mapping.")

            output_definition = next(
                output for output in capability.outputs if output.name == output_name
            )
            self._validate_typed_value(
                output_name,
                extracted,
                output_definition.type,
            )

            outputs[
                output_name
            ] = extracted

            print(
                f"Extracted: "
                f"{extracted}"
            )

            self.logger.log(
                "output_extracted",
                name=output_name,
                value=extracted
            )

    def _detect_business_outcome(
        self,
        include_validation=False,
    ):
        if self.handoff_manager and self.handoff_manager.requires_handoff():
            self._perform_handoff("The application requires manual verification.")

        consume_dialog = getattr(self.surface, "consume_unexpected_dialog", None)
        dialog_message = consume_dialog() if consume_dialog else None
        if dialog_message:
            return self._handoff_or_failure(
                "UNEXPECTED_DIALOG",
                "An unexpected browser dialog interrupted replay.",
                handoff_reason="An unexpected browser dialog requires review.",
            )

        validation_errors = self.surface.validation_errors() if include_validation else []
        if validation_errors:
            return ReplayResult(
                status=ReplayStatus.BUSINESS_OUTCOME,
                outputs={},
                code="INVALID_INPUT",
                message="; ".join(validation_errors),
                recovered_steps=self.recovered_steps,
            )
        body_text = self.surface.body_text()
        normalized = " ".join(body_text.lower().split())

        if "session expired" in normalized or "session has expired" in normalized:
            return self._handoff_or_failure(
                "SESSION_EXPIRED",
                "The authenticated session expired.",
                handoff_reason="The session expired and must be restored manually.",
            )

        if any(
            marker in normalized
            for marker in ("authentication required", "sign in required", "login required")
        ):
            return self._handoff_or_failure(
                "AUTHENTICATION_REQUIRED",
                "Authentication is required before replay can continue.",
                handoff_reason="Authentication is required to continue replay.",
            )

        if any(
            marker in normalized
            for marker in ("permission denied", "access denied", "not authorized", "forbidden")
        ):
            return self._runtime_failure(
                "PERMISSION_DENIED",
                "The current operator is not authorized for this operation.",
            )

        if "account locked" in normalized:
            return ReplayResult(
                status=ReplayStatus.BUSINESS_OUTCOME,
                outputs={},
                code="ACCOUNT_LOCKED",
                message="Account locked",
                recovered_steps=self.recovered_steps,
            )

        if any(
            marker in normalized
            for marker in ("member verification failed", "verification failed")
        ):
            return self._handoff_or_failure(
                "VERIFICATION_FAILED",
                "Member verification failed.",
                handoff_reason="Member verification failed and requires human review.",
            )

        if (
            "Member not found"
            in body_text
        ):
            print(
                "\nBUSINESS OUTCOME: "
                "Member not found"
            )

            return ReplayResult(
                status=(
                    ReplayStatus
                    .BUSINESS_OUTCOME
                ),
                outputs={},
                code="MEMBER_NOT_FOUND",
                message="Member not found",
                recovered_steps=(
                    self.recovered_steps
                )
            )

        return None

    def _raise_transient_application_state(self):
        normalized = " ".join(self.surface.body_text().lower().split())
        if any(
            marker in normalized
            for marker in (
                "temporarily unavailable",
                "service unavailable",
                "try again later",
            )
        ):
            raise RuntimeConditionError(
                "APP_TEMPORARILY_UNAVAILABLE",
                "The application is temporarily unavailable.",
                retryable=True,
            )

    def _handoff_or_failure(self, code, message, handoff_reason):
        if self.handoff_manager is not None:
            self._perform_handoff(handoff_reason)
            return None
        return self._runtime_failure(code, message)

    def _runtime_failure(self, code, message):
        return ReplayResult(
            status=ReplayStatus.FAILURE,
            outputs={},
            code=code,
            message=message,
            failed_step=self.current_step_id,
            recovered_steps=self.recovered_steps,
        )

    def _log_outcome(self, result):
        event = (
            "business_outcome"
            if result.status == ReplayStatus.BUSINESS_OUTCOME
            else "replay_failed"
        )
        self.logger.log(event, code=result.code, message=result.message)

    def _perform_handoff(self, reason):
        self.handoff_count += 1
        context = {
            "capability_id": self.active_capability_id,
            "step_id": self.current_step_id,
            "url": self.surface.current_url(),
            "page_title": self.surface.page_title(),
        }
        self.logger.log("handoff_started", reason=reason, control_owner="human", **context)
        try:
            result = self.handoff_manager.handoff(reason=reason, context=context)
        except HandoffCancelled:
            self.logger.log("handoff_cancelled", control_owner="human",
                            human_action_type="terminated_run", **context)
            raise
        self.logger.log(
            "handoff_completed",
            handoff_number=self.handoff_count,
            control_owner="automation",
            capability_id=self.active_capability_id,
            step_id=self.current_step_id,
            url=self.surface.current_url(),
            screenshot=result["screenshot"],
            human_action=result["human_action"],
            human_action_type=result.get(
                "human_action_type", "completed_manual_intervention"
            ),
        )

    def _failure_result(
        self,
        step,
        error
    ):
        print(
            f"\nHARD FAILURE "
            f"AT {step.step_id}"
        )

        print(
            f"Reason: {error}"
        )

        evidence_path = (
            self._capture_failure_evidence(
                step.step_id
            )
        )

        return ReplayResult(
            status=ReplayStatus.FAILURE,
            outputs={},
            code=(
                error.code
                if isinstance(error, RuntimeConditionError)
                else "STEP_EXECUTION_FAILED"
            ),
            message=str(error),
            failed_step=step.step_id,
            expected=(
                self._expected_for_step(
                    step
                )
            ),
            observed=(
                self._current_page_summary()
            ),
            recovered_steps=(
                self.recovered_steps
            ),
            evidence_path=evidence_path
        )

    def _final_failure_result(
        self,
        error
    ):
        evidence_path = (
            self._capture_failure_evidence(
                "success_condition"
            )
        )
        return ReplayResult(
            status=ReplayStatus.FAILURE,
            outputs={},
            code="SUCCESS_CONDITION_FAILED",
            message=str(error),
            expected=(
                "Capability success condition "
                "should be satisfied."
            ),
            observed=(
                self._current_page_summary()
            ),
            recovered_steps=(
                self.recovered_steps
            ),
            evidence_path=evidence_path
        )

    def _output_contract_failure_result(self, error):
        evidence_path = self._capture_failure_evidence("output_contract")
        return ReplayResult(
            status=ReplayStatus.FAILURE,
            outputs={},
            code="OUTPUT_CONTRACT_FAILED",
            message=str(error),
            expected="Every declared capability output should be extracted.",
            observed=self._current_page_summary(),
            recovered_steps=self.recovered_steps,
            evidence_path=evidence_path,
        )

    def _identity_failure_result(self, error):
        evidence_path = self._capture_failure_evidence("identity_mismatch")
        return ReplayResult(
            status=ReplayStatus.FAILURE,
            outputs={},
            code="MEMBER_IDENTITY_MISMATCH",
            message=str(error),
            failed_step=self.current_step_id,
            expected="Displayed member number should match the requested member_id.",
            observed=self._current_page_summary(),
            recovered_steps=self.recovered_steps,
            evidence_path=evidence_path,
        )

    def _capture_failure_evidence(
        self,
        name
    ):
        path = Path(
            "evidence"
        ) / f"failure_{name}.png"

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            self.surface.screenshot(str(path))

            print(
                f"Failure evidence saved: "
                f"{path}"
            )

            return str(path)

        except Exception as error:
            print(
                "Could not capture "
                f"failure screenshot: {error}"
            )

            return None

    def _expected_for_step(
        self,
        step
    ):
        if step.target:
            return (
                f"Action "
                f"'{step.action.value}' "
                f"on target "
                f"'{step.target.name}'."
            )

        return (
            f"Action "
            f"'{step.action.value}' "
            "should complete."
        )

    def _current_page_summary(
        self
    ):
        try:
            title = self.surface.page_title()
            url = self.surface.current_url()
            body_text = self.surface.body_text()

            body_text = (
                " ".join(
                    body_text.split()
                )
            )

            body_text = (
                body_text[:300]
            )

            return (
                f"Title={title}; "
                f"URL={url}; "
                f"Page={body_text}"
            )

        except Exception as error:
            return (
                "Unable to observe "
                f"current page: {error}"
            )

    def _validate_inputs(
        self,
        capability,
        inputs
    ):
        for parameter in (
            capability.parameters
        ):
            if (
                parameter.required
                and parameter.name
                not in inputs
            ):
                raise ValueError(
                    "Missing required input: "
                    f"{parameter.name}"
                )
            if parameter.name in inputs:
                self._validate_typed_value(parameter.name, inputs[parameter.name], parameter.type)

        declared = {parameter.name for parameter in capability.parameters}
        unexpected = set(inputs) - declared
        if unexpected:
            raise ValueError(f"Unexpected input(s): {', '.join(sorted(unexpected))}")

    def _validate_business_inputs(self, capability, inputs):
        if capability.capability_id == "prepare_deposit" and "amount" in inputs:
            try:
                amount = float(inputs["amount"])
            except (TypeError, ValueError):
                amount = -1
            if amount < 0.01 or amount > 10000:
                return ReplayResult(
                    status=ReplayStatus.BUSINESS_OUTCOME,
                    outputs={},
                    code="INVALID_AMOUNT",
                    message="Deposit amount must be between $0.01 and $10,000.",
                    recovered_steps=self.recovered_steps,
                )
        return None

    def _verify_requested_identity(self, inputs):
        if "member_id" not in inputs:
            return
        displayed = self.surface.extract_labeled_value("Member Number")
        requested = str(inputs["member_id"])
        if displayed != requested:
            raise IdentityMismatchError(
                f"Displayed member number '{displayed}' does not match requested member_id."
            )

    @staticmethod
    def _validate_outputs(capability, outputs):
        declared = {output.name for output in capability.outputs}
        missing = sorted(declared - set(outputs))
        if missing:
            raise OutputContractError(
                f"Missing declared output(s): {', '.join(missing)}"
            )

    @staticmethod
    def _validate_typed_value(name, value, expected_type):
        valid = {
            DataType.STRING: isinstance(value, str),
            DataType.INTEGER: isinstance(value, int) and not isinstance(value, bool),
            DataType.NUMBER: isinstance(value, (int, float)) and not isinstance(value, bool),
            DataType.BOOLEAN: isinstance(value, bool),
        }[expected_type]
        if not valid:
            raise TypeError(f"Value '{name}' must be {expected_type.value}.")

    def _resolve_value(
        self,
        template,
        inputs
    ):
        if template is None:
            return None

        match = re.fullmatch(
            r"\{\{(.+?)\}\}",
            template
        )

        if not match:
            return template

        parameter_name = (
            match.group(1)
        )

        if (
            parameter_name
            not in inputs
        ):
            raise ValueError(
                "Missing input value: "
                f"{parameter_name}"
            )

        return str(
            inputs[
                parameter_name
            ]
        )

    def _find_target(
        self,
        target
    ):
        return self.surface.find_target(target)

    def _extract_value(
        self,
        label
    ):
        return self.surface.extract_labeled_value(label)

    def _check_success(
        self,
        capability
    ):
        condition = (
            capability
            .success_condition
        )

        if condition.type.value == "text_present":
            body_text = (
                self.surface.body_text()
            )

            if (
                condition.value
                not in body_text
            ):
                raise RuntimeError(
                    "Success condition "
                    "failed. Expected text: "
                    f"{condition.value}"
                )
        elif condition.type.value == "title_equals":
            if self.surface.page_title() != condition.value:
                raise RuntimeError(f"Expected page title: {condition.value}")
        elif condition.type.value == "url_matches":
            if re.fullmatch(condition.value, self.surface.current_url()) is None:
                raise RuntimeError(f"URL did not match: {condition.value}")
