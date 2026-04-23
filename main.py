try:
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
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.primary_hue = "700"
        return Builder.load_string(KV)

    def on_mic_press(self):
        print("Listening...")
        self.root.ids.status_label.text = "Listening..."


if __name__ == "__main__":
    HeliosApp().run()
