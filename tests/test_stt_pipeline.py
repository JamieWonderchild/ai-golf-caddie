import asyncio
import pytest

from golfcaddie.pipecat_pipeline import MockPipecatPipeline


@pytest.mark.asyncio
async def test_mock_pipecat_pipeline_events():
    """Test the MockPipecatPipeline with transcript events."""
    events = [
        ("partial", "hello", 10),
        ("partial", "hello wor", 10),
        ("final", "hello world", 20),
    ]
    
    pipeline = MockPipecatPipeline(events)
    transcripts = []
    
    def on_transcript(text: str, is_final: bool):
        transcripts.append((text, is_final))
    
    pipeline.set_callbacks(on_transcript=on_transcript)
    
    # Start pipeline and wait for events
    await pipeline.start()
    await asyncio.sleep(0.5)  # Allow time for events to process
    await pipeline.stop()
    
    # Verify we got the expected transcripts
    expected = [("hello", False), ("hello wor", False), ("hello world", True)]
    assert transcripts == expected


@pytest.mark.asyncio
async def test_mock_pipecat_pipeline_speak():
    """Test the speak method of MockPipecatPipeline."""
    pipeline = MockPipecatPipeline([])
    
    await pipeline.start()
    await pipeline.speak("Test message")  # Should not raise exception
    await pipeline.stop()
    
    assert True  # Test passes if no exception is raised


def test_mock_pipecat_pipeline_is_running():
    """Test the is_running method."""
    pipeline = MockPipecatPipeline([])
    
    assert not pipeline.is_running()
    
    # Note: We can't easily test the running state without async context
    # This is a limitation of the current test setup

