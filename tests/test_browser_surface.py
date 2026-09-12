from src.surface.browser import BrowserSurface


surface = BrowserSurface(headless=False)

try:
    surface.start()

    surface.navigate("http://127.0.0.1:5001")

    observation = surface.observe()

    print("\nBANKPILOT OBSERVATION")
    print("---------------------")

    print(
        observation.model_dump_json(indent=2)
    )

    input("\nPress Enter to close the browser...")

finally:
    surface.close()