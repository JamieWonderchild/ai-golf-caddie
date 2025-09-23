from __future__ import annotations

import asyncio
import threading
import time
from typing import Callable, Optional

import speechmatics
from speechmatics.models import (
    AudioSettings,
    ConnectionSettings,
    ServerMessageType,
    TranscriptionConfig,
)


class MockSttPipeline:
    """Mock STT pipeline for testing."""

    def __init__(self, events: list[tuple[str, str, float]]):
        self.events = events
        self._on_partial: Optional[Callable[[str], None]] = None
        self._on_final: Optional[Callable[[str], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.metrics = type('Metrics', (), {
            'p50_p90': lambda self: (10.0, 20.0, 15.0, 25.0)
        })()

    def set_callbacks(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ):
        """Set callback functions for partial and final transcripts."""
        self._on_partial = on_partial
        self._on_final = on_final

    def start(self):
        """Start the mock pipeline."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_mock)
        self._thread.start()

    def stop(self):
        """Stop the mock pipeline."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_mock(self):
        """Run the mock events."""
        for event_type, text, timestamp in self.events:
            if not self._running:
                break
            time.sleep(0.1)  # Simulate processing time
            if event_type == "partial" and self._on_partial:
                # Mock pipeline expects (text, timestamp) signature
                self._on_partial(text, timestamp)
            elif event_type == "final" and self._on_final:
                # Mock pipeline expects (text, start, end, confidence) signature
                self._on_final(text, timestamp - 10, timestamp, None)


class SpeechmaticsPipeline:
    """Speechmatics real-time transcription pipeline using the official Python client."""

    def __init__(
        self,
        api_key: str,
        language: str = "en",
        device: Optional[str] = None,
        sample_rate: int = 16000,
    ):
        self._api_key = api_key
        self._language = language
        self._device = device
        self._sample_rate = sample_rate
        self._on_partial: Optional[Callable[[str], None]] = None
        self._on_final: Optional[Callable[[str], None]] = None
        self._ws: Optional[speechmatics.client.WebsocketClient] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def set_callbacks(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ):
        """Set callback functions for partial and final transcripts."""
        self._on_partial = on_partial
        self._on_final = on_final

    def start(self):
        """Start the transcription pipeline."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_sync)
        self._thread.start()

    def stop(self):
        """Stop the transcription pipeline."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_sync(self):
        """Run the transcription pipeline synchronously."""
        try:
            # Create connection settings
            connection_settings = ConnectionSettings(
                url="wss://eu2.rt.speechmatics.com/v2",
                auth_token=self._api_key,
            )

            # Create WebSocket client
            self._ws = speechmatics.client.WebsocketClient(connection_settings)

            # Set up event handlers
            if self._on_partial:
                self._ws.add_event_handler(
                    ServerMessageType.AddPartialTranscript,
                    self._handle_partial_transcript,
                )

            if self._on_final:
                self._ws.add_event_handler(
                    ServerMessageType.AddTranscript,
                    self._handle_final_transcript,
                )

            # Audio settings - specify the format explicitly
            audio_settings = AudioSettings(
                encoding="pcm_s16le",
                sample_rate=self._sample_rate,
            )

            # Transcription config
            transcription_config = TranscriptionConfig(
                language=self._language,
                enable_partials=True,
                operating_point="enhanced",
                max_delay=1.0,
            )

            print("✅ Starting Speechmatics transcription...")

            # Try a simpler approach - use a file-like object
            import io
            import queue
            import threading
            
            # Create a queue to hold audio data
            audio_queue = queue.Queue()
            
            # Set up microphone
            import sounddevice as sd
            
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"Audio status: {status}")
                # Convert to bytes and put in queue
                audio_bytes = indata.tobytes()
                audio_queue.put(audio_bytes)
            
            stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                callback=audio_callback,
                blocksize=int(self._sample_rate * 0.02),  # 20ms blocks
                device=self._device,
            )
            stream.start()
            
            # Create a BytesIO object that reads from the queue
            class QueueAudioStream(io.BytesIO):
                def __init__(self, audio_queue):
                    super().__init__()
                    self.audio_queue = audio_queue
                    self._buffer = b""
                
                def read(self, size=-1):
                    # If we have data in buffer, return it
                    if self._buffer:
                        if size == -1:
                            data = self._buffer
                            self._buffer = b""
                            return data
                        else:
                            data = self._buffer[:size]
                            self._buffer = self._buffer[size:]
                            return data
                    
                    # Otherwise, get new data from queue
                    try:
                        new_data = self.audio_queue.get(timeout=0.1)
                        self._buffer += new_data
                        
                        if size == -1:
                            data = self._buffer
                            self._buffer = b""
                            return data
                        else:
                            data = self._buffer[:size]
                            self._buffer = self._buffer[size:]
                            return data
                    except queue.Empty:
                        return b""
            
            # Create audio stream
            audio_stream = QueueAudioStream(audio_queue)
            
            # Run the WebSocket client
            self._ws.run_synchronously(audio_stream, transcription_config, audio_settings)

        except Exception as e:
            # Suppress noisy shutdown errors after we intentionally stop
            if self._running:
                print(f"❌ Transcription error: {e}")
        finally:
            self._running = False

    def _handle_partial_transcript(self, msg):
        """Handle partial transcript messages."""
        if self._on_partial:
            transcript = msg.get("metadata", {}).get("transcript", "")
            if transcript:
                self._on_partial(transcript)

    def _handle_final_transcript(self, msg):
        """Handle final transcript messages."""
        if self._on_final:
            transcript = msg.get("metadata", {}).get("transcript", "")
            if transcript:
                self._on_final(transcript)
