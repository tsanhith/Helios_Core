import os
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

try:
    import requests
    from kivy.clock import Clock
    from kivy.lang import Builder
    from kivymd.app import MDApp
    from kivymd.uix.button import MDRaisedButton
    from kivymd.uix.dialog import MDDialog
    from plyer import recorder, tts
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
    COMMAND_URL = "http://127.0.0.1:8000/process"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_recording = False
        self.audio_file = None
        self.session_id = self._init_session()

    def _init_session(self) -> str:
        """Initialize or load session ID."""
        import json
        session_file = Path(__file__).parent / ".helios_session"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                return data.get("session_id", str(uuid.uuid4())[:8])
            except Exception:
                pass
        session_id = str(uuid.uuid4())[:8]
        session_file.write_text(json.dumps({"session_id": session_id}))
        return session_id

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.primary_hue = "700"
        return Builder.load_string(KV)

    def on_mic_press(self):
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        import tempfile
        self.is_recording = True
        self.root.ids.status_label.text = "Recording..."
        self.root.ids.mic_button.icon = "stop"
        self.audio_file = os.path.join(tempfile.gettempdir(), "helios_audio.wav")
        recorder.start(self.audio_file)

    def _stop_recording(self):
        self.is_recording = False
        self.root.ids.status_label.text = "Processing..."
        self.root.ids.mic_button.icon = "microphone"
        recorder.stop()

        threading.Thread(
            target=self._transcribe_audio,
            daemon=True,
        ).start()

    def _transcribe_audio(self):
        try:
            import riva.client
            import grpc

            api_key = os.environ.get("NVIDIA_API_KEY", "")
            if not api_key:
                raise ValueError("NVIDIA_API_KEY environment variable not set in .env")

            # Riva ASR via NVIDIA NIM
            server = "grpc.nvcf.nvidia.com:443"
            function_id = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"  # whisper-large-v3

            # Create SSL channel with metadata interceptor
            channel = grpc.secure_channel(
                server,
                grpc.ssl_channel_credentials()
            )

            # Add metadata for authentication
            auth_metadata_plugin = riva.client.CustomMetadataPlugin(
                [
                    ("function-id", function_id),
                    ("authorization", f"Bearer {api_key}"),
                ]
            )
            channel = grpc.intercept_channel(channel, auth_metadata_plugin)

            # Create ASR client
            asr_client = riva.client.SpeechRecognitionService(channel)

            # Configure recognition - mono 16-bit WAV
            config = riva.client.StreamingRecognitionConfig(
                interim_results=False,
                config=riva.client.RecognitionConfig(
                    encoding=riva.client.AudioEncoding.LINEAR_PCM,
                    sample_rate_hertz=16000,
                    language_code="en-US",
                    max_alternatives=1,
                    enable_automatic_punctuation=True,
                ),
            )

            # Transcribe file (offline mode)
            audio_chunks = riva.client.AudioChunkFileIterator(
                self.audio_file,
                16000,  # sample rate
                8000,   # chunk size
            )
            responses = asr_client.offline_recognize(audio_chunks, config)

            results = []
            for response in responses:
                if response.results:
                    for result in response.results:
                        if result.alternatives:
                            results.append(result.alternatives[0].transcript)

            text = " ".join(results).strip()
            print(f"Transcribed: {text}")

            if text:
                Clock.schedule_once(lambda _dt: self._send_command(text))
            else:
                Clock.schedule_once(lambda _dt: self._update_status_label("No speech detected"))

        except Exception as exc:
            error_msg = f"Transcription failed: {exc}"
            print(error_msg)
            Clock.schedule_once(lambda _dt: self._update_status_label(error_msg))

    def _send_command(self, command: str):
        try:
            response = requests.post(
                self.COMMAND_URL,
                json={"text": command, "session_id": self.session_id},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            print(f"Server response: {data}")
            result_text = data.get("message", str(data))
            actions = data.get("actions", [])
            confirmation_required = data.get("confirmation_required", False)

            if actions:
                action_types = [a.get("type", "unknown") for a in actions]
                result_text = f"{result_text}\nActions: {', '.join(action_types)}"

            # Speak the response
            self._speak(result_text)

            # Check if confirmation is required for any action
            if confirmation_required:
                sensitive_actions = [a for a in actions if a.get("confirmation_required", False)]
                if sensitive_actions:
                    Clock.schedule_once(
                        lambda _dt: self._show_confirmation_dialog(sensitive_actions, result_text)
                    )
                    return

        except requests.RequestException as exc:
            result_text = f"Request failed: {exc}"
            print(result_text)
            self._speak("Sorry, there was a network error.")
        except ValueError as exc:
            result_text = f"Invalid JSON response: {exc}"
            print(result_text)
            self._speak("Sorry, I received an invalid response.")

        Clock.schedule_once(lambda _dt: self._update_status_label(result_text))

    def _speak(self, text: str):
        """Use TTS to speak the response."""
        try:
            # Extract just the main message before newlines
            speak_text = text.split('\n')[0] if '\n' in text else text
            tts.speak(speak_text)
        except Exception as e:
            print(f"TTS error: {e}")

    def _show_confirmation_dialog(self, actions: list, message: str):
        """Show confirmation dialog for sensitive actions."""
        action_details = []
        for action in actions:
            action_type = action.get("type", "unknown")
            params = action.get("params", {})
            if action_type == "call":
                action_details.append(f"Call {params.get('contact', 'unknown')}")
            elif action_type == "sms":
                action_details.append(f"Message {params.get('contact', 'unknown')}")
            elif action_type == "email":
                action_details.append(f"Email {params.get('recipient', 'unknown')}")
            else:
                action_details.append(f"{action_type}: {params}")

        dialog_text = f"{message}\n\nActions:\n" + "\n".join(f"  - {d}" for d in action_details)

        self.dialog = MDDialog(
            title="Confirm Action",
            text=dialog_text,
            buttons=[
                MDRaisedButton(
                    text="Cancel",
                    on_release=lambda _: self._dismiss_dialog(),
                ),
                MDRaisedButton(
                    text="Confirm",
                    on_release=lambda _: self._confirm_action(actions),
                ),
            ],
        )
        self.dialog.open()

    def _dismiss_dialog(self):
        """Dismiss confirmation dialog."""
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()
        self._update_status_label("Action cancelled")

    def _confirm_action(self, actions: list):
        """Handle confirmed actions."""
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()

        # Execute confirmed actions
        action_names = [a.get("type", "unknown") for a in actions]
        self._update_status_label(f"Executing: {', '.join(action_names)}")

        # Here you would actually execute the actions on the device
        # For now, just speak and update status
        self._speak("Action confirmed and executing")

        # Execute each action
        for action in actions:
            self._execute_action(action)

    def _execute_action(self, action: dict):
        """Execute a single action."""
        action_type = action.get("type")
        params = action.get("params", {})

        try:
            if action_type == "call":
                phone = params.get("contact", "")
                print(f"[EXECUTE] Calling {phone}")
                # Import android_intent or similar for actual execution

            elif action_type == "sms":
                phone = params.get("contact", "")
                message = params.get("message", "")
                print(f"[EXECUTE] SMS to {phone}: {message}")

            elif action_type == "open_app":
                app_name = params.get("app", "")
                print(f"[EXECUTE] Opening app: {app_name}")

            elif action_type == "speak":
                text = params.get("text", "")
                self._speak(text)

            elif action_type == "email":
                recipient = params.get("recipient", "")
                subject = params.get("subject", "")
                body = params.get("body", "")
                print(f"[EXECUTE] Email to {recipient}: {subject}")

            elif action_type == "reminder":
                reminder_text = params.get("text", "")
                when = params.get("datetime", "")
                print(f"[EXECUTE] Reminder: {reminder_text} at {when}")

            elif action_type == "web_search":
                query = params.get("query", "")
                print(f"[EXECUTE] Web search: {query}")

            elif action_type == "calendar_add":
                title = params.get("title", "")
                event_time = params.get("datetime", "")
                print(f"[EXECUTE] Calendar event: {title} at {event_time}")

        except Exception as e:
            print(f"[ERROR] Failed to execute {action_type}: {e}")

    def _update_status_label(self, text: str):
        self.root.ids.status_label.text = text


if __name__ == "__main__":
    HeliosApp().run()
