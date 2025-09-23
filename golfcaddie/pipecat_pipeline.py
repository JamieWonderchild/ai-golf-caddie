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
from pipecat.transports.local.audio import LocalAudioInputTransport, LocalAudioTransportParams
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
        """Process frames - pass all through, capture transcriptions."""
        
        # Handle transcription frames (STT output)
        if isinstance(frame, TranscriptionFrame):
            if self._on_transcript:
                self._on_transcript(frame.text, True)  # final transcript
        elif isinstance(frame, InterimTranscriptionFrame):
            if self._on_transcript:
                self._on_transcript(frame.text, False)  # interim transcript
                
        # Always pass frame through - let Pipecat handle all frame lifecycle
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
        self._audio_input: Optional[LocalAudioInputTransport] = None
        
    def set_callbacks(
        self,
        on_transcript: Optional[Callable[[str, bool], None]] = None,
    ):
        """Set callback functions for handling transcription."""
        self._on_transcript = on_transcript
        
    async def _create_pipeline(self) -> Pipeline:
        """Create and configure the Pipecat pipeline."""
        print("[PIPELINE_CREATE] Starting pipeline creation...")
        
        # Create InputParams for STT service (fixes deprecation warning)
        from pipecat.services.speechmatics.stt import SpeechmaticsSTTService
        
        # Create input parameters with proper language configuration
        input_params = SpeechmaticsSTTService.InputParams(
            language=self.config.language,
            enable_partials=True,  # Enable partial transcriptions for real-time feedback
            enable_vad=False,  # Disable VAD since we handle audio transport separately
            max_delay=1.0,  # Maximum delay for transcription
            end_of_utterance_silence_trigger=0.5,  # Silence trigger duration
        )
        
        # Create STT service with proper parameters
        self._stt_service = SpeechmaticsSTTService(
            api_key=self.config.api_key,
            sample_rate=self.config.sample_rate,
            params=input_params,
        )
        
        
        
        # Create PyAudio instance
        py_audio = pyaudio.PyAudio()
        
        # Parse device index if provided (could be string index or device name)
        device_index = None
        if self.config.device is not None:
            try:
                device_index = int(self.config.device)
            except ValueError:
                # If device is a string name, we'd need to enumerate devices to find index
                # For now, fall back to None (default device)
                logger.warning(f"Device '{self.config.device}' not found as index, using default")
                device_index = None
        
        # Create audio input transport with proper parameters
        audio_params = LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_in_sample_rate=self.config.sample_rate,
            audio_in_channels=1,
            input_device_index=device_index
        )
        
        self._audio_input = LocalAudioInputTransport(
            py_audio=py_audio,
            params=audio_params
        )
        
        # Install transcript hook immediately after STT service is created
        print(f"[PRE_HOOK] About to install hook. Callback: {self._on_transcript}, STT service: {self._stt_service}")
        self._install_transcript_hook()
        print("[POST_HOOK] Hook installation completed")
        
        # Build pipeline (STT only, TTS handled separately)
        # For now, use pipeline without custom processor to avoid frame lifecycle issues
        pipeline = Pipeline([
            self._audio_input,
            self._stt_service,
        ])
        
        return pipeline
    
    def _install_transcript_hook(self):
        """Install the transcript hook after pipeline creation."""
        print(f"[DEBUG] Installing hook, callback: {self._on_transcript}")
        if self._on_transcript and self._stt_service:
            print("[SETUP] Installing _send_frames hook...")
            original_send_frames = self._stt_service._send_frames
            
            def hooked_send_frames(frames):
                print(f"[DIRECT_HOOK] _send_frames called with {len(frames)} frames")
                
                # Process frames to extract transcripts
                for frame in frames:
                    print(f"[DIRECT_HOOK] Frame type: {type(frame).__name__}")
                    if hasattr(frame, 'text') and frame.text:
                        print(f"[DIRECT_HOOK] Found transcript: '{frame.text}'")
                        # Check if it's a final transcript
                        is_final = type(frame).__name__ == 'TranscriptionFrame'
                        print(f"[DIRECT_HOOK] Calling callback: is_final={is_final}")
                        self._on_transcript(frame.text, is_final)
                
                # Call the original method
                return original_send_frames(frames)
            
            # Replace the method
            self._stt_service._send_frames = hooked_send_frames
            print("[SETUP] Successfully hooked into _send_frames method")
        else:
            print("[SETUP] No transcript callback or STT service, skipping hook")
        
    async def start(self):
        """Start the pipeline."""
        print("[START_METHOD] Pipeline start() method called")
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