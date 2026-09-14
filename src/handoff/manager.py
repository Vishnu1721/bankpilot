from pathlib import Path


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
        screenshot_path = Path("evidence/handoff_required.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.surface.page.screenshot(path=str(screenshot_path), full_page=True)
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
            "and press Enter (blank uses the default): "
        ).strip()
        if not human_action:
            human_action = "Completed required manual member verification."

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
