import json
import re
from pathlib import Path

from src.capability.models import (
    Capability,
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
    SafetyPolicy
)


class ReplayEngine:

    def __init__(
        self,
        surface,
        safety_policy=None,
        max_retries=2,
        retry_delay_ms=500,
        log_path="evidence/replay_log.jsonl"
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
                    self.surface.page.url
                )

                business_result = (
                    self._detect_business_outcome()
                )

                if business_result:
                    self.logger.log(
                        "business_outcome",
                        code=business_result.code,
                        message=(
                            business_result.message
                        )
                    )

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

                except Exception as error:
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
                    self._detect_business_outcome()
                )

                if business_result:
                    self.logger.log(
                        "business_outcome",
                        code=business_result.code,
                        message=(
                            business_result.message
                        )
                    )

                    return business_result

            try:
                self._check_success(
                    capability
                )

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
                self._execute_step(
                    step,
                    capability,
                    inputs,
                    outputs
                )

                if attempt > 1:
                    print(
                        "Recovered after "
                        f"{attempt - 1} retry(s)."
                    )

                    return True

                return False

            except Exception as error:
                last_error = error

                if (
                    attempt
                    > self.max_retries
                ):
                    break

                print(
                    "Recoverable condition "
                    f"at {step.step_id}: "
                    f"{error}"
                )

                print(
                    f"Retrying "
                    f"({attempt}/"
                    f"{self.max_retries})..."
                )

                self.logger.log(
                    "step_retry",
                    step_id=step.step_id,
                    attempt=attempt,
                    error=str(error)
                )

                self.surface.wait(
                    self.retry_delay_ms
                )

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
            step.target
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

            locator = self._find_target(
                step.target
            )

            locator.fill(
                value
            )

        elif (
            step.action
            == StepType.SELECT
        ):
            value = self._resolve_value(
                step.value,
                inputs
            )

            locator = self._find_target(
                step.target
            )

            # Prefer the human-readable option label recorded at discovery.
            locator.select_option(
                label=value
            )

        elif (
            step.action
            == StepType.CLICK
        ):
            locator = self._find_target(
                step.target
            )

            locator.click()

            self.surface.page.wait_for_load_state(
                "domcontentloaded"
            )

            self.safety.check_url(
                self.surface.page.url
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
            extracted = self._extract_value(
                step.value
            )

            output_name = (
                capability.outputs[0].name
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
        self
    ):
        body_text = (
            self.surface.page
            .locator("body")
            .inner_text()
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
            code="STEP_EXECUTION_FAILED",
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

            self.surface.page.screenshot(
                path=str(path),
                full_page=True
            )

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
        if (
            self.surface.page
            is None
        ):
            return (
                "No active browser page."
            )

        try:
            title = (
                self.surface.page.title()
            )

            url = (
                self.surface.page.url
            )

            body_text = (
                self.surface.page
                .locator("body")
                .inner_text()
            )

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
        if target is None:
            raise ValueError(
                "Replay step has "
                "no target."
            )

        if (
            target.role
            and target.name
        ):
            try:
                locator = (
                    self.surface.page
                    .get_by_role(
                        target.role,
                        name=target.name
                    )
                )

                if (
                    locator.count()
                    == 1
                ):
                    return locator

            except Exception:
                pass

        if target.selector:
            locator = (
                self.surface.page
                .locator(
                    target.selector
                )
            )

            if (
                locator.count()
                == 1
            ):
                return locator

        raise RuntimeError(
            "Unable to locate "
            f"target: {target.name}"
        )

    def _extract_value(
        self,
        label
    ):
        rows = (
            self.surface.page
            .locator("tr")
        )

        for index in range(
            rows.count()
        ):
            row = (
                rows.nth(index)
            )

            text = (
                row.inner_text()
                .strip()
            )

            if (
                label.lower()
                in text.lower()
            ):
                cells = (
                    row.locator("td")
                )

                if (
                    cells.count()
                    >= 2
                ):
                    return (
                        cells.nth(1)
                        .inner_text()
                        .strip()
                    )

        raise RuntimeError(
            "Could not extract "
            f"value for: {label}"
        )

    def _check_success(
        self,
        capability
    ):
        condition = (
            capability
            .success_condition
        )

        if (
            condition.type
            == "text_present"
        ):
            body_text = (
                self.surface.page
                .locator("body")
                .inner_text()
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
