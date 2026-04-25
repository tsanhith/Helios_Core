try:
    import threading
    import requests
    from kivy.clock import Clock
    from kivy.lang import Builder
    from kivymd.app import MDApp
except ModuleNotFoundError as exc:
    missing_pkg = exc.name or "a required package"
    raise SystemExit(
        f"Missing dependency: {missing_pkg}. Install dependencies with: "
        "python -m pip install -r requirements.txt"
    ) from exc

KV = """
MDScreen:
    MDBoxLayout:
        orientation: "vertical"
        spacing: "16dp"
        size_hint: None, None
        size: dp(260), dp(320)
        pos_hint: {"center_x": 0.5, "center_y": 0.5}

        Widget:

        MDIconButton:
            id: mic_button
            icon: "microphone"
            icon_size: "108sp"
            pos_hint: {"center_x": 0.5}
            theme_icon_color: "Custom"
            icon_color: 1, 1, 1, 1
            md_bg_color: app.theme_cls.primary_color
            on_release: app.on_mic_press()

        MDLabel:
            id: status_label
            text: "Ready"
            halign: "center"
            font_style: "H5"

        Widget:
"""


class HeliosApp(MDApp):
    COMMAND_URL = "http://127.0.0.1:8000/process_command"

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.primary_hue = "700"
        return Builder.load_string(KV)

    def on_mic_press(self):
        simulated_command = "Message John"
        print(f"Simulated voice command: {simulated_command}")
        self.root.ids.status_label.text = "Sending command..."
        threading.Thread(
            target=self._send_command,
            args=(simulated_command,),
            daemon=True,
        ).start()

    def _send_command(self, command: str):
        try:
            response = requests.post(
                self.COMMAND_URL,
                json={"command": command},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            print(f"Server response: {data}")
            result_text = data.get("result", str(data)) if isinstance(data, dict) else str(data)
        except requests.RequestException as exc:
            result_text = f"Request failed: {exc}"
            print(result_text)
        except ValueError as exc:
            result_text = f"Invalid JSON response: {exc}"
            print(result_text)

        Clock.schedule_once(lambda _dt: self._update_status_label(result_text))

    def _update_status_label(self, text: str):
        self.root.ids.status_label.text = text


if __name__ == "__main__":
    HeliosApp().run()
