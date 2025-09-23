# Golf Caddie Voice Agent

A voice-powered golf caddie that uses **Pipecat with Speechmatics** real-time Speech‑to‑Text (STT), OpenAI for witty recommendations, Speechmatics Text‑to‑Speech (TTS) for playback, Open‑Meteo for live wind, and OSM Nominatim for course lookup.

## Features

- 🎤 **Pipecat + Speechmatics STT**: real-time voice pipeline with live mic capture and transcription
- 🧭 Course lookup (OSM Nominatim): “first tee of <course>” → lat/lon
- 🌬️ Weather (Open‑Meteo): headwind/crosswind summary cached for session
- 🧠 Session memory: recent shots, current conditions, and hole layout
- 🤖 OpenAI: concise, humorous club/shot recommendations
- 🔊 Speechmatics TTS: speaks both conditions and recommendations

## Quick Start

### Prerequisites

- Python 3.8+
- PortAudio (for microphone access)
- Speechmatics API key

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd speechmatics-takehome
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Install PortAudio** (for microphone):
   ```bash
   # Ubuntu/Debian
   sudo apt install portaudio19-dev
   
   # macOS
   brew install portaudio
   
   # Windows
   # Download from: https://www.portaudio.com/download.html
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Required
   SPEECHMATICS_API_KEY=...
   OPENAI_API_KEY=...
   # Optional
   SPEECHMATICS_WS_URL=wss://eu2.rt.speechmatics.com/v2
   SPEECHMATICS_TTS_URL=https://preview.tts.speechmatics.com/generate
   SPEECHMATICS_LANG=en
   ```

### Usage

**Live voice interaction**:
```bash
python -m golfcaddie.cli listen --handicap=20 --lat=51.5074 --lon=-0.1278 --bearing=0
```

**Check weather**:
```bash
python -m golfcaddie.cli weather 51.5074 -0.1278 0
```

## Architecture

### Core Components

- **`pipecat_pipeline.py`**: Pipecat framework integration with Speechmatics STT/TTS services
- **`geocode.py`**: OSM Nominatim course lookup
- **`weather.py`**: Open‑Meteo wind integration with summary
- **`llm.py`**: Prompt builder and OpenAI call
- **`cli.py`**: Command-line interface with async Pipecat pipeline orchestration

### Data Flow

1. **Voice Input** → **Pipecat Pipeline** → Speechmatics STT → Transcript
2. **Transcript** → Intent Parser → Structured Golf Context
3. **Context + Weather** → Recommendation Engine → Club/Shot Suggestion
4. **Suggestion** → Humor Generator → Witty Response
5. **Response** → **Pipecat Pipeline** → Speechmatics TTS → Audio Output

### External Data Sources

- **Speechmatics Real-time API**: Live speech transcription and TTS via Pipecat integration
- **Open-Meteo API**: Current wind speed and direction
- **OSM Nominatim**: Course geocoding to lat/lon

## Configuration

### Environment Variables

```bash
# Required
SPEECHMATICS_API_KEY=your_api_key_here

# Optional
SPEECHMATICS_WS_URL=wss://eu2.rt.speechmatics.com/v2
SPEECHMATICS_TTS_URL=https://preview.tts.speechmatics.com/generate
SPEECHMATICS_LANG=en
```

### CLI flags

- `--debug`: show verbose logs (geocode URL, coords, prompt, OpenAI meta, TTS diagnostics)
- `--replay`: offer to replay/delete the temporary TTS WAV after playback

## Testing

Run the comprehensive test suite:
```bash
python -m pytest tests/ -v
```

Tests include:
- Unit tests for all modules
- Mocked external API calls
- Integration tests for CLI commands
- STT pipeline testing with mock data

## Trade-offs Made

### Technical Notes

- **Pipecat Framework**: Real-time voice pipeline orchestrating Speechmatics STT/TTS services
- **Async Architecture**: Full async/await implementation with proper resource management
- **Mock Support**: Testing mode with `--mock` flag for development and CI/CD
- Session memory caches: conditions/coords, hole layout, and last few shot exchanges

### APIs

- **Pipecat + Speechmatics**: Official Pipecat integration for STT/TTS services
- Open‑Meteo weather (HTTP)
- OSM Nominatim geocoding (HTTP)

### Troubleshooting

- Mic capture fails → install PortAudio; ensure `sounddevice` can enumerate devices
- TTS DNS error → falls back to preview endpoint; try `--debug` to inspect
- No audio output → use `--replay` to save WAV and test playback

## AI/LLM Usage

This project uses **Pipecat framework** to orchestrate real-time voice interactions with:
- **Speechmatics** for Speech-to-Text (STT) and Text-to-Speech (TTS) services
- **OpenAI** for intelligent golf recommendations and context understanding

## Demo Scenarios

Try these voice commands:

- “I’m on the first tee of Finchley Golf Club — what are the conditions?”
- “I’m 150 yards in the rough with water right”
- “Hole 2 is a dogleg right with bunkers short left”

The system will provide club recommendations, shot types, aim adjustments, and humorous commentary based on your handicap, current conditions, and learned preferences.

## Future Enhancements

- Course and hole lookup via OpenStreetMap
- Integration with golf GPS apps
- Multi-language support
- Advanced weather modeling
- Integration with golf tracking devices
