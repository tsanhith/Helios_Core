import os
import threading
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

try:
    import requests
    from kivy.clock import Clock
    from kivy.lang import Builder
    from kivymd.app import MDApp
    from plyer import recorder
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_recording = False
        self.audio_file = None

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
