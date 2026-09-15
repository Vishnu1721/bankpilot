from pathlib import Path
import hashlib


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
            "and press Enter (a blank response cannot resume): "
        ).strip()
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
            "url": url,
            "screenshot": str(screenshot_path),
        }

    def _state_fingerprint(self):
        page = self.surface.page
        payload = f"{page.url}\n{page.title()}\n{page.locator('body').inner_text()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
