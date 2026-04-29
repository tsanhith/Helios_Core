"""Wake word detection for Helios."""

import threading
import time
from pathlib import Path
from typing import Callable, Optional


class WakeWordDetector:
    """Wake word detector using OpenWakeWord or VAD fallback.

    For now, this is a simplified implementation that can be expanded
    with actual wake word model detection when openwakeword is installed.
    """

    WAKE_WORDS = ["hey helios", "helios", "okay helios", "hi helios", "hello helios"]

    def __init__(self,
                 on_wake: Callable,
                 sample_rate: int = 16000,
                 buffer_duration: float = 2.0):
        """Initialize wake word detector.

        Args:
            on_wake: Callback function when wake word detected
            sample_rate: Audio sample rate in Hz
            buffer_duration: Buffer duration in seconds
        """
        self.on_wake = on_wake
        self.sample_rate = sample_rate
        self.buffer_duration = buffer_duration

        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Try to use openwakeword if available
        self._oww = None
        self._oww_available = False
        try:
            import openwakeword
            from openwakeword.model import Model
            self._oww_available = True
            print("OpenWakeWord available")
        except ImportError:
            print("OpenWakeWord not available, using text-based fallback")

    def _detect_wake_word(self, audio_data: bytes) -> bool:
        """Check if audio contains wake word."""
        if self._oww_available:
            # Use OpenWakeWord model
            # This would require loading the model and processing audio
            # For now, just return False as placeholder
            return False
        else:
            # Fallback: can't detect from raw audio without ASR
            return False

    def _listen_loop(self):
        """Background listening loop."""
        while self._running:
            # In a real implementation, this would:
            # 1. Capture audio from microphone continuously
            # 2. Process through VAD (Voice Activity Detection)
            # 3. Run wake word detection on audio chunks
            # 4. Call on_wake when detected

            # For now, this is a placeholder
            time.sleep(0.1)

    def start(self):
        """Start wake word detection."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("Wake word detector started")

    def stop(self):
        """Stop wake word detection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("Wake word detector stopped")

    def is_running(self) -> bool:
        """Check if detector is running."""
        return self._running


class TextWakeWordDetector:
    """Simple text-based wake word detection for development/testing.

    This is useful for testing the wake word flow without having
    actual audio wake word detection.
    """

    WAKE_WORDS = ["hey helios", "helios", "okay helios", "hi helios", "hello helios"]

    def __init__(self, on_wake: Callable):
        self.on_wake = on_wake

    def check_text(self, text: str) -> bool:
        """Check if text contains wake word.

        Args:
            text: Text to check

        Returns:
            True if wake word detected
        """
        text_lower = text.lower().strip()

        # Check if text starts with or contains wake word
        for wake_word in self.WAKE_WORDS:
            if text_lower.startswith(wake_word) or wake_word in text_lower:
                # Extract command after wake word
                command = text_lower.split(wake_word, 1)[-1].strip()
                self.on_wake(command if command else None)
                return True

        return False


class VADWakeWordDetector:
    """VAD-based wake word detection placeholder.

    This uses WebRTC VAD or similar to detect speech,
    then sends audio for ASR to check for wake word.
    """

    def __init__(self,
                 on_wake: Callable,
                 sample_rate: int = 16000,
                 frame_duration: int = 30):
        """Initialize VAD-based detector.

        Args:
            on_wake: Callback when wake word + command detected
            sample_rate: Audio sample rate
            frame_duration: Frame duration in ms (10, 20, or 30)
        """
        self.on_wake = on_wake
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration

        self._vad = None
        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(3)  # Aggressiveness 0-3
        except ImportError:
            print("WebRTC VAD not available")

    def process_frame(self, frame: bytes) -> bool:
        """Process an audio frame.

        Returns:
            True if speech detected
        """
        if self._vad:
            try:
                import webrtcvad
                return self._vad.is_speech(frame, self.sample_rate)
            except Exception as e:
                print(f"VAD error: {e}")
        return False
