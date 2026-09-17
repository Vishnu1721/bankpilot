from pathlib import Path
import hashlib


class HandoffCancelled(RuntimeError):
    """Operator explicitly terminated the run; never resume automation."""


class HumanHandoffManager:

    def __init__(
        self,
        surface
    ):
        self.surface = surface

    def requires_handoff(
        self
    ):
        body_text = (
            self.surface.page
            .locator("body")
            .inner_text()
        )

        return (
            "Manual Verification Required"
            in body_text
        )

    def handoff(
        self,
        reason,
        context=None,
    ):
        context = context or {}
        before_state = self._state_fingerprint()
        screenshot_path = Path("evidence/handoff_required.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.surface.screenshot(str(screenshot_path))
        url = self.surface.page.url
        print(
            "\n================================"
        )

        print(
            "HUMAN INTERVENTION REQUIRED"
        )

        print(
            "================================"
        )

        print(
            f"\nReason: {reason}"
        )
        print(f"Capability: {context.get('capability_id', 'unknown')}")
        print(f"Current step: {context.get('step_id', 'unknown')}")
        print(f"URL: {url}")
        print(f"Screenshot: {screenshot_path}")
        print("Control owner: human")

        print(
            "\nThe browser will remain open."
        )

        print(
            "Complete the required action "
            "manually in the SAME browser."
        )

        human_action = input(
            "\nAfter completing verification, briefly describe what you did "
            "and press Enter, or type /cancel to terminate (blank cannot resume): "
        ).strip()
        if human_action.lower() == "/cancel":
            raise HandoffCancelled("Operator cancelled the intervention; automation stopped.")
        if not human_action:
            raise RuntimeError("Resume rejected: describe the completed human action.")
        if self._state_fingerprint() == before_state:
            raise RuntimeError("Resume rejected: the live session state did not change.")

        print(
            "\nHuman intervention completed."
        )

        print(
            "Resuming automation..."
        )
        print("Control owner: automation")

        return {
            "control_owner": "automation",
            "human_action": human_action,
            "human_action_type": self._action_type(reason),
            "url": url,
            "screenshot": str(screenshot_path),
        }

    @staticmethod
    def _action_type(reason):
        normalized = reason.lower()
        if "untrusted ui" in normalized or "injection" in normalized:
            return "reviewed_untrusted_ui"
        if "verification" in normalized:
            return "completed_manual_verification"
        if "session" in normalized or "authentication" in normalized:
            return "restored_authenticated_session"
        if "permission" in normalized:
            return "resolved_permission_block"
        if "dialog" in normalized:
            return "resolved_unexpected_dialog"
        return "completed_manual_intervention"

    def _state_fingerprint(self):
        page = self.surface.page
        payload = f"{page.url}\n{page.title()}\n{page.locator('body').inner_text()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
