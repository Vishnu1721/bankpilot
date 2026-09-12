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
        reason
    ):
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

        print(
            "\nThe browser will remain open."
        )

        print(
            "Complete the required action "
            "manually in the SAME browser."
        )

        input(
            "\nAfter completing verification, "
            "press Enter here to resume..."
        )

        print(
            "\nHuman intervention completed."
        )

        print(
            "Resuming automation..."
        )