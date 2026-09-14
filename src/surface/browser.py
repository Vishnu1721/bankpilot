from pathlib import Path

from playwright.sync_api import sync_playwright

from src.agent.models import Observation, UIElement


class BrowserSurface:

    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        return self

    def navigate(self, url):
        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")

    def observe(self):
        elements = []
        controls = self.page.locator("input, button, select, textarea, a")

        for index in range(controls.count()):
            control = controls.nth(index)
            if not control.is_visible():
                continue

            tag = control.evaluate("(el) => el.tagName.toLowerCase()")
            elements.append(
                UIElement(
                    element_id=f"e{len(elements) + 1}",
                    role=self._get_role(control, tag),
                    name=self._get_element_name(control, tag),
                    selector=self._build_selector(control, tag),
                    value=self._get_element_value(control, tag),
                )
            )

        # inner_text returns rendered text; hidden DOM text is not sent to the LLM.
        return Observation(
            url=self.page.url,
            title=self.page.title(),
            text=self.page.locator("body").inner_text(),
            elements=elements,
            trust="untrusted_ui_data",
        )

    def execute(self, action, observation):
        if action.element_id is None:
            raise ValueError("This action requires an element_id.")

        element = self._find_element(action.element_id, observation)

        if action.action.value == "type":
            if action.value is None:
                raise ValueError("Type action requires a value.")
            self.fill(element.selector, action.value)
        elif action.action.value == "select":
            if action.value is None:
                raise ValueError("Select action requires a value.")
            self.page.locator(element.selector).select_option(label=action.value)
        elif action.action.value == "click":
            self.click(element.selector)
        else:
            raise ValueError(f"Unsupported browser action: {action.action.value}")

    def _find_element(self, element_id, observation):
        for element in observation.elements:
            if element.element_id == element_id:
                return element
        raise ValueError(f"Element {element_id} was not found in the current observation.")

    def fill(self, selector, value):
        self.page.locator(selector).fill(value)

    def click(self, selector):
        self.page.locator(selector).click()
        self.page.wait_for_load_state("domcontentloaded")

    def wait(self, milliseconds=1000):
        self.page.wait_for_timeout(milliseconds)

    def screenshot(self, path):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(output), full_page=True)

    def _get_role(self, control, tag):
        if tag == "input":
            input_type = control.get_attribute("type") or "text"
            if input_type in ("text", "email", "password", "number"):
                return "textbox"
            return "input"
        return {
            "button": "button",
            "select": "select",
            "textarea": "textbox",
            "a": "link",
        }.get(tag, tag)

    def _get_element_name(self, control, tag):
        aria_label = control.get_attribute("aria-label")
        if aria_label:
            return aria_label.strip()

        if tag in ("button", "a"):
            return " ".join(control.inner_text().split())

        element_id = control.get_attribute("id")
        if element_id:
            label = self.page.locator(f'label[for="{element_id}"]')
            if label.count():
                return label.first.inner_text().strip()

        name = control.get_attribute("name")
        if name:
            return name.replace("_", " ").title()

        return control.get_attribute("placeholder") or tag

    def _get_element_value(self, control, tag):
        if tag in ("input", "textarea", "select"):
            return control.input_value()
        return None

    def _build_selector(self, control, tag):
        # Prefer stable attributes. Never interpolate rendered multi-line text
        # into CSS because quotes/newlines can produce invalid selectors.
        for attribute in ("data-testid", "aria-label", "name"):
            value = control.get_attribute(attribute)
            if value:
                escaped = self._escape_css_attribute(value)
                return f'{tag}[{attribute}="{escaped}"]'

        element_id = control.get_attribute("id")
        if element_id:
            escaped = self._escape_css_attribute(element_id)
            return f'[id="{escaped}"]'

        if tag == "a":
            href = control.get_attribute("href")
            if href:
                escaped = self._escape_css_attribute(href)
                return f'a[href="{escaped}"]'

        # Last-resort XPath stays valid for multiline and quoted visible text.
        return control.evaluate(
            """(el) => {
                const parts = [];
                while (el && el.nodeType === 1) {
                    let position = 1;
                    let sibling = el.previousElementSibling;
                    while (sibling) {
                        if (sibling.tagName === el.tagName) position += 1;
                        sibling = sibling.previousElementSibling;
                    }
                    parts.unshift(
                        el.tagName.toLowerCase() + "[" + position + "]"
                    );
                    el = el.parentElement;
                }
                return "xpath=/" + parts.join("/");
            }"""
        )

    @staticmethod
    def _escape_css_attribute(value):
        return (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\a ")
            .replace("\r", "")
        )

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
