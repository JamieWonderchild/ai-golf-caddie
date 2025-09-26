"""Pipecat-based audio pipeline using Speechmatics STT service."""

from __future__ import annotations

import asyncio
import os
from typing import Optional, Callable, Any
from dataclasses import dataclass

from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    InterimTranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    StartFrame,
    EndFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.services.speechmatics.stt import SpeechmaticsSTTService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
import pyaudio

from .tts import speak as speechmatics_speak
from loguru import logger


@dataclass
class PipelineConfig:
    """Configuration for the Pipecat pipeline."""
    api_key: str
    language: str = "en"
    sample_rate: int = 16000
    device: Optional[str] = None


class GolfCaddieProcessor(FrameProcessor):
    """Minimal processor that captures transcription frames."""
    
    def __init__(
        self, 
        on_transcript: Optional[Callable[[str, bool], None]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._on_transcript = on_transcript
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames - capture transcripts and pass through."""

        # IMPORTANT: let base class handle StartFrame/system frames first
        await super().process_frame(frame, direction)

        # Capture STT frames only
        if isinstance(frame, TranscriptionFrame):
            if self._on_transcript and getattr(frame, "text", None):
                self._on_transcript(frame.text, True)
        elif isinstance(frame, InterimTranscriptionFrame):
            if self._on_transcript and getattr(frame, "text", None):
                self._on_transcript(frame.text, False)

        # Pass frame along
        await self.push_frame(frame, direction)


class PipecatGolfPipeline:
    """Pipecat-based golf caddie pipeline with Speechmatics STT."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._runner: Optional[PipelineRunner] = None
        self._task: Optional[PipelineTask] = None
        self._on_transcript: Optional[Callable[[str, bool], None]] = None
        
        # Pipeline components
        self._stt_service: Optional[SpeechmaticsSTTService] = None
        self._processor: Optional[GolfCaddieProcessor] = None
        self._audio_transport: Optional[LocalAudioTransport] = None
        
    def set_callbacks(
        self,
        on_transcript: Optional[Callable[[str, bool], None]] = None,
    ):
        """Set callback functions for handling transcription."""
        self._on_transcript = on_transcript
        
    async def _create_pipeline(self) -> Pipeline:
        """Create and configure the Pipecat pipeline."""
        
        # CRITICAL: enable_partials=True is REQUIRED for real-time transcription!
        from pipecat.transcriptions.language import Language

        # Configure Speechmatics STT service with optimized settings for natural speech
        self._stt_service = SpeechmaticsSTTService(
            api_key=self.config.api_key,
            base_url="wss://eu2.rt.speechmatics.com/v2",
            sample_rate=self.config.sample_rate,
            params=SpeechmaticsSTTService.InputParams(
                language=Language.EN,
                enable_partials=True,
                max_delay=3.0,  # Allow 3 seconds for natural speech pauses
                chunk_size=160, # Keep chunk size small for responsiveness
                enable_vad=True,  # Use Voice Activity Detection for better speech boundary detection
                end_of_utterance_silence_trigger=3.0,  # Allow 3 seconds of silence before ending utterance
            )
        )
        
        
        
        # Resolve input device if provided (by index or name substring)
        input_device_index = None
        if self.config.device is not None:
            try:
                # Accept integer indices directly
                input_device_index = int(self.config.device)
            except (TypeError, ValueError):
                try:
                    p = pyaudio.PyAudio()
                    for i in range(p.get_device_count()):
                        info = p.get_device_info_by_index(i)
                        name = info.get("name", "")
                        if self.config.device.lower() in name.lower() and info.get("maxInputChannels", 0) > 0:
                            input_device_index = i
                            break
                except Exception as _e:
                    logger.warning(f"Could not resolve device '{self.config.device}': {_e}")

        # Create audio transport using LocalAudioTransportParams
        transport_params = LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_in_sample_rate=self.config.sample_rate,
            audio_in_channels=1,
            input_device_index=input_device_index,
        )
        
        self._audio_transport = LocalAudioTransport(params=transport_params)

        # Add a processor after STT to capture outgoing transcription frames
        self._processor = GolfCaddieProcessor(on_transcript=self._on_transcript)

        # Build pipeline: mic -> STT -> processor
        pipeline = Pipeline([
            self._audio_transport.input(),
            self._stt_service,
            self._processor,
        ])
        
        return pipeline
    
    def _install_transcript_hook(self):
        """Deprecated: previously hooked internal methods; no longer used."""
        logger.debug("Transcript hook not used; processor captures frames downstream.")
        
    async def start(self):
        """Start the pipeline."""
        if self._runner is not None:
            logger.warning("Pipeline already running")
            return
            
        try:
            pipeline = await self._create_pipeline()
            
            self._task = PipelineTask(pipeline)
            self._runner = PipelineRunner()
            
            logger.info("Starting Pipecat pipeline with Speechmatics STT/TTS")
            await self._runner.run(self._task)
            
        except Exception as e:
            logger.error(f"Failed to start pipeline: {e}")
            raise
            
    async def stop(self):
        """Stop the pipeline."""
        if self._runner is None:
            return
            
        try:
            logger.info("Stopping Pipecat pipeline")
            await self._runner.stop()
            self._runner = None
            self._task = None
            
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")
            
    async def speak(self, text: str):
        """Send text to TTS using original Speechmatics implementation."""
        try:
            # Use the original Speechmatics TTS implementation
            await asyncio.to_thread(speechmatics_speak, text)
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._runner is not None


class MockPipecatPipeline:
    """Mock pipeline for testing."""
    
    def __init__(self, events: list[tuple[str, str, float]]):
        self.events = events
        self._on_transcript: Optional[Callable[[str, bool], None]] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    def set_callbacks(
        self,
        on_transcript: Optional[Callable[[str, bool], None]] = None,
    ):
        """Set callback functions for mock events."""
        self._on_transcript = on_transcript
        
    async def start(self):
        """Start the mock pipeline."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._run_mock_events())
        
    async def stop(self):
        """Stop the mock pipeline."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            
    async def speak(self, text: str):
        """Mock speak method."""
        logger.info(f"Mock TTS: {text}")
        
    def is_running(self) -> bool:
        """Check if mock pipeline is running."""
        return self._running
        
    async def _run_mock_events(self):
        """Run mock transcription events."""
        try:
            for event_type, text, timestamp in self.events:
                if not self._running:
                    break
                    
                await asyncio.sleep(0.1)  # Simulate processing time
                
                if self._on_transcript:
                    is_final = event_type == "final"
                    self._on_transcript(text, is_final)
                    
        except asyncio.CancelledError:
            pass