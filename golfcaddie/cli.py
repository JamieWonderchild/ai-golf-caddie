from typing import Optional
import click
import time
import asyncio
from dotenv import load_dotenv
import sys
import select
import re

from . import weather as weather_mod
from .pipecat_pipeline import PipecatGolfPipeline, MockPipecatPipeline, PipelineConfig
from .llm import build_prompt, ask_openai
from .geocode import geocode_course, extract_course_name
from .parser import parse_intent


def _detect_intent(text: str) -> str:
    """Return 'weather' if clearly asking about weather/conditions; otherwise 'shot'."""
    l = text.lower()
    # Shot intent keywords/phrases - be more specific to avoid false positives
    shot_keys = [
        "what club",
        "which club",
        "recommend",
        "suggest",
        "should i",
        "what should i play",
        "how should i play",
        "should i hit",
        "hit",
        "aim",
        "carry",
        "lay up",
        "club do i use",
        "use a",
    ]
    has_shot = any(k in l for k in shot_keys)

    # Weather-specific question forms; avoid triggering on mere mentions like "into the wind"
    weather_q_patterns = [
        r"\bwhat(?:'s| is)?\b.*\b(wind|weather|conditions|forecast)\b",
        r"\bhow\b.*\b(windy|wind)\b",
        r"\bcurrent\b.*\b(conditions|wind|weather)\b",
        r"\bforecast\b",
        r"\btell me.*\b(about|the)?\b.*\b(conditions|weather|wind)\b",
        r"\bcan you tell me.*\b(conditions|weather|wind)\b",
        r"\bwhat are.*\b(conditions|weather|wind)\b",
        r"\bcheck.*\b(conditions|weather|wind)\b",
        r"\b(conditions|weather|wind).*\b(today|now|current)\b",
        r"\b(today|now).*\b(conditions|weather|wind)\b",
    ]
    has_weather_q = any(re.search(p, l) for p in weather_q_patterns)

    if has_weather_q and not has_shot:
        return "weather"
    # Default to shot guidance when ambiguous or both are present
    return "shot"


@click.group()
def cli():
    """Golf Caddie CLI"""
    pass


@cli.command()
@click.argument('lat', type=float)
@click.argument('lon', type=float)
@click.argument('bearing', type=int)
def weather(lat: float, lon: float, bearing: int):
    """Get current wind conditions for a course location."""
    wind = weather_mod.get_wind(lat, lon, bearing)
    click.echo(f"Wind: {wind.summary}")
    click.echo(f"Headwind: {wind.headwind_ms:.1f} m/s")
    click.echo(f"Crosswind: {wind.crosswind_ms:.1f} m/s")


## simulate command removed (legacy, rule-based path)


@cli.command()
@click.option('--api-key', help='Speechmatics API key (overrides env)')
@click.option('--mock', is_flag=True, default=False, help='Use mock pipeline for testing')
@click.option('--language', default='en', help='Language')
@click.option('--device', help='Mic device (sounddevice name/index)')
@click.option('--lat', default=51.5074, help='Course latitude')
@click.option('--lon', default=-0.1278, help='Course longitude')
@click.option('--bearing', default=0, help='Target bearing (deg)')
@click.option('--handicap', default=20, help='User handicap')
@click.option('--openai', is_flag=True, default=False, help='(Deprecated) OpenAI mode is now the default')
@click.option('--debug/--no-debug', default=False, help='Show verbose debug output')
@click.option('--replay/--no-replay', default=False, help='Prompt to replay/delete TTS WAV')
def listen(api_key: Optional[str], mock: bool, language: str, 
           device: Optional[str], lat: float, lon: float, 
           bearing: int, handicap: int, openai: bool, debug: bool, replay: bool):
    """Live mic: transcribe with Speechmatics and output recommendations."""
    # Load environment variables from .env file
    load_dotenv()
    
    import os
    api_key = api_key or os.getenv("SPEECHMATICS_API_KEY")
    # Pipecat handles URL configuration internally
    if not api_key:
        click.echo("Error: SPEECHMATICS_API_KEY not set", err=True)
        raise click.Abort()

    # Configure debug/replay via env for downstream modules
    if debug:
        os.environ["GC_DEBUG"] = "1"
        click.echo("(debug) Verbose logging enabled")
    else:
        os.environ.pop("GC_DEBUG", None)
    if replay:
        os.environ["GC_TTS_REPLAY"] = "1"
    else:
        os.environ.pop("GC_TTS_REPLAY", None)
    
    # Rule-based pipeline removed. We now always use OpenAI for recommendations.

    # Session cache for coords/conditions/handicap
    if not hasattr(listen, "_session_cache"):
        listen._session_cache = {"coords": None, "conditions": None, "current_handicap": handicap}  # type: ignore[attr-defined]

    # Session state for automatic transcript processing
    processing_lock = asyncio.Lock()
    
    async def process_transcript_automatically(transcript: str):
        """Process a transcript automatically when STT finalizes it."""
        if not transcript.strip():
            return
            
        async with processing_lock:
            if debug:
                click.echo("--- Captured Transcript ---")
                click.echo(transcript)
            
            click.echo(f"🎤 Transcript: {transcript}")
            
            # Parse the intent and extract any handicap mention
            intent = _detect_intent(transcript)
            parsed_intent = parse_intent(transcript, listen._session_cache.get("current_handicap"))  # type: ignore[attr-defined]
            
            # Update current handicap if mentioned in speech
            if parsed_intent.handicap_mentioned is not None:
                listen._session_cache["current_handicap"] = parsed_intent.handicap_mentioned  # type: ignore[attr-defined]
                if debug:
                    click.echo(f"[HANDICAP] Updated to {parsed_intent.handicap_mentioned} from speech")
            
            current_handicap = listen._session_cache.get("current_handicap", handicap)  # type: ignore[attr-defined]

            # If the user mentions specific course/hole context, attempt to refresh coords and cache conditions silently
            try:
                lower = transcript.lower()
                if any(k in lower for k in ("first tee", "clubhouse", "course")) or re.search(r"\bhole\s+\d+\b", lower):
                    course = extract_course_name(transcript)
                    if debug:
                        print(f"[LOC] course_query='{course}'")
                    lat2, lon2 = geocode_course(course)
                    listen._session_cache["coords"] = (lat2, lon2)  # type: ignore[attr-defined]
                    # Pre-fetch conditions for LLM context only; do not speak unless explicitly asked
                    try:
                        w_tmp = weather_mod.get_wind(lat2, lon2, bearing)
                        listen._session_cache["conditions"] = w_tmp.summary  # type: ignore[attr-defined]
                        if debug:
                            click.echo(f"[LOC] coords=({lat2:.5f},{lon2:.5f}) cached_conditions={w_tmp.summary}")
                    except Exception as _e:
                        if debug:
                            click.echo(f"[LOC] weather cache failed: {_e}")
            except Exception as e:
                if debug:
                    click.echo(f"[LOC] extraction/geocode failed: {e}")

            # If explicitly asking about weather/conditions, fetch and speak them
            if intent == "weather":
                coords = listen._session_cache.get("coords")  # type: ignore[attr-defined]
                use_lat, use_lon = (coords if coords else (lat, lon))
                try:
                    w = weather_mod.get_wind(use_lat, use_lon, bearing)
                    listen._session_cache["conditions"] = w.summary  # type: ignore[attr-defined]
                    click.echo("--- Conditions ---")
                    click.echo(w.summary)
                    await pipe.speak(w.summary)
                    click.echo("🎧 Ready for next question...")
                    return
                except Exception as e:
                    click.echo(f"Weather error: {e}", err=True)
                    return

            coords = listen._session_cache.get("coords")  # type: ignore[attr-defined]
            conds = listen._session_cache.get("conditions")  # type: ignore[attr-defined]
            use_lat, use_lon = (coords if coords else (lat, lon))

            # Maintain simple hole layout memory: if user mentions "next hole" or similar, clear it
            if not hasattr(listen, "_hole_layout"):
                listen._hole_layout = None  # type: ignore[attr-defined]
            if any(p in lower for p in ("next hole", "new hole", "on the next", "moved to")) or re.search(r"\bhole\s+\d+\b", lower):
                listen._hole_layout = None  # type: ignore[attr-defined]
            # If user describes layout (trees left/right, water right, dogleg), capture a brief summary
            if any(k in lower for k in ("bunker", "trees", "water", "dogleg", "narrow", "wide", "elevated", "downhill", "uphill")):
                # Keep a short rolling description
                listen._hole_layout = (transcript if len(transcript) < 240 else transcript[:240])  # type: ignore[attr-defined]

            prompt = build_prompt(
                transcript,
                current_handicap,
                use_lat,
                use_lon,
                bearing,
                history=getattr(listen, "_history", None),
                conditions=conds,
                hole_layout=getattr(listen, "_hole_layout", None),
            )
            
            if debug:
                click.echo("--- Prompt To OpenAI ---")
                click.echo(prompt)
                click.echo("--- Asking OpenAI... ---")
            
            click.echo("🤔 Processing your request...")
            
            if not hasattr(listen, "_history"):
                listen._history = []  # type: ignore[attr-defined]

            try:
                reply, meta = ask_openai(prompt)
                if debug:
                    click.echo("--- OpenAI Reply ---")
                    click.echo(reply)
                    click.echo("--- OpenAI Meta ---")
                    click.echo(str(meta))
                
                click.echo(f"🧠 Response: {reply}")
                await pipe.speak(reply)
                listen._history.append((transcript, reply))  # type: ignore[attr-defined]
                if len(listen._history) > 10:  # type: ignore[attr-defined]
                    listen._history = listen._history[-10:]  # type: ignore[attr-defined]
                click.echo("🎧 Ready for next question...")
            except Exception as e:
                click.echo(f"OpenAI error: {e}", err=True)

    def on_transcript_callback(text: str, is_final: bool):
        """Callback from Pipecat pipeline for transcripts."""
        if is_final:
            # Process final transcripts automatically
            asyncio.create_task(process_transcript_automatically(text))
        else:
            # Just show interim transcripts
            if text.strip():
                click.echo(f"🎤 Listening: {text}", nl=False)
                click.echo("\r", nl=False)

    # Create Pipecat pipeline configuration
    config = PipelineConfig(
        api_key=api_key,
        language=language,
        device=device,
    )
    
    # Use mock pipeline for testing if requested
    if mock:
        mock_events = [
            ("partial", "I'm on the first tee", 1.0),
            ("final", "I'm on the first tee of Finchley Golf Club", 2.0),
        ]
        pipe = MockPipecatPipeline(mock_events)
    else:
        pipe = PipecatGolfPipeline(config)
    
    # Set the callback BEFORE starting the pipeline
    print(f"[DEBUG] Setting transcript callback: {on_transcript_callback}")
    pipe.set_callbacks(on_transcript=on_transcript_callback)
    click.echo("🎧 Listening... When you see a transcript in the logs, copy and paste it below to process:")
    click.echo("💡 Or type 'q' to quit, Ctrl+C also works")

    async def run_pipeline():
        """Run the Pipecat pipeline asynchronously."""
        try:
            await pipe.start()
            
            # Simple loop - let Pipecat handle STT, provide manual input option
            while True:
                try:
                    # Simple prompt for manual input when needed
                    line = await asyncio.to_thread(input, "")
                    
                    if line.strip().lower() in ("q", "quit", "exit"):
                        break
                    elif line.strip():  # Any non-empty input triggers processing
                        await process_transcript_automatically(line.strip())
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            await pipe.stop()

    
    # Run the async pipeline
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
