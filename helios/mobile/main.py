"""Helios Core mobile app."""

import os
import sys
from pathlib import Path

# Add parent to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from kivy.clock import Clock
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel

from shared.config import Config

KV = """
MDScreen:
    MDFloatLayout:
        MDBoxLayout:
            orientation: "vertical"
            spacing: 20
            padding: 20
            size_hint: 0.9, 0.8
            pos_hint: {"center_x": 0.5, "center_y": 0.5}

            MDLabel:
                text: "Helios Core"
                halign: "center"
                font_style: "H3"
                size_hint_y: None
                height: self.texture_size[1]

            MDTextField:
                id: command_input
                hint_text: "Type your command..."
                mode: "rectangle"

            MDRaisedButton:
                text: "Send"
                pos_hint: {"center_x": 0.5}
                on_release: app.send_command()

            MDLabel:
                id: response_label
                text: ""
                halign: "center"
                theme_text_color: "Secondary"
"""


class HeliosApp(MDApp):
    """Main mobile app."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_url = f"{Config.BACKEND_HOST}/process"

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        return Builder.load_string(KV)

    def send_command(self):
        """Send command to backend."""
        text = self.root.ids.command_input.text.strip()
        if not text:
            return

        self.root.ids.response_label.text = "Processing..."

        def _send():
            try:
                response = requests.post(
                    self.api_url,
                    json={"text": text},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                actions = data.get("actions", [])
                message = data.get("message", "Done")

                result = f"{message}"
                if actions:
                    result += f"\nActions: {len(actions)}"

            except Exception as e:
                result = f"Error: {e}"

            Clock.schedule_once(lambda _: self._update_response(result))

        Clock.schedule_once(lambda _: _send())

    def _update_response(self, text: str):
        self.root.ids.response_label.text = text


if __name__ == "__main__":
    HeliosApp().run()
