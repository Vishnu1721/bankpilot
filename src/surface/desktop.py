class DesktopSurface:
    """Safe extension point for an accessibility-tree desktop adapter.

    Pixel-coordinate clicking and arbitrary keystrokes are deliberately absent.
    Implementations must expose stable element IDs, foreground-app allowlisting,
    and the same observe/execute contract as BrowserSurface.
    """

    def __init__(self, allowed_applications=None):
        self.allowed_applications = set(allowed_applications or ())
        self.active_application = None

    def start(self):
        raise NotImplementedError(
            "Connect a platform accessibility provider before desktop use."
        )

    def navigate(self, target):
        if target not in self.allowed_applications:
            raise ValueError("Desktop application is not allowlisted.")
        self.active_application = target

    def observe(self):
        raise NotImplementedError("Accessibility-tree observation is not configured.")

    def execute(self, action, observation):
        raise NotImplementedError("Desktop action execution is not configured.")

    def wait(self, milliseconds=1000):
        return None

    def screenshot(self, path):
        raise NotImplementedError

    def close(self):
        return None
