# SAGE - Smart Adaptive General Executive

🚀 **Zero-Cost AI Desktop Assistant** - A modular, Python-based AI assistant that runs entirely on free and open-source technologies.

## 🎯 Project Vision

SAGE is designed to be a comprehensive AI assistant that:
- **Costs $0** - No API fees, all models run locally or use free tiers
- **Learns from you** - Adapts to your preferences and usage patterns  
- **Works offline** - Core functionality doesn't require internet
- **Stays modular** - Easy to add/remove features without breaking others
- **Runs efficiently** - Optimized for laptop performance

## ✨ Features

### 🎤 Voice Interface
- **Speech Recognition**: Whisper (local), Google Speech (free), Vosk (offline)
- **Text-to-Speech**: pyttsx3 (offline), edge-tts (free Microsoft TTS)
- **Wake Word Detection**: Porcupine (free tier), Snowboy
- **Real-time Processing**: Voice activity detection, noise reduction

### 🧠 Local AI & NLP
- **Local LLM**: Ollama integration (Phi3, Llama 3.2, Mistral)
- **Intent Parsing**: spaCy-based natural language understanding
- **Context Memory**: Maintains conversation history and context
- **Command Shortcuts**: Quick access to frequently used functions

### 👁️ Computer Vision (Optional)
- **Face Recognition**: Local face_recognition library
- **Object Detection**: YOLOv8 (local inference)
- **OCR**: Tesseract for text extraction
- **Screen Analysis**: Automated screen capture and analysis

### 📅 Smart Calendar & Scheduling
- **Natural Language**: "Remind me tomorrow at 3pm about the meeting"
- **Local Storage**: SQLite-based scheduling system
- **Smart Reminders**: Context-aware notification system

### 🌐 Web Integration
- **Free Search**: DuckDuckGo, Google (no API key needed)
- **Web Scraping**: BeautifulSoup, Selenium for dynamic content
- **Free APIs**: Weather, news, and other services (free tiers)

### 🔧 Office Integration
- **Excel/Word**: Read and manipulate Office documents
- **File Monitoring**: Watch for file changes and respond
- **Clipboard Integration**: Smart clipboard management

### 🧩 3D & Fabrication (Optional)
- **3D Processing**: STL file handling with trimesh
- **G-code Generation**: For 3D printing and CNC
- **CAD Integration**: Basic 3D model processing

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- 4GB+ RAM recommended
- Microphone and speakers for voice features

### Installation

1. **Clone and Setup**:
```bash
git clone <your-repo-url>
cd SAGE
python scripts/setup.py
```

2. **Activate Environment**:
```bash
# Linux/Mac
source venv/bin/activate

# Windows  
venv\\Scripts\\activate
```

3. **Run SAGE**:
```bash
python main.py
```

Or use the startup scripts:
```bash
# Linux/Mac
./start_sage.sh

# Windows
start_sage.bat
```

### First Run Configuration

SAGE will create default configuration files on first run. Key settings:

- **Voice**: Enabled by default with Whisper (tiny model)
- **AI**: Uses Ollama with Phi3 Mini model
- **Wake Word**: "sage" (can be changed in config.yaml)

## 📁 Project Structure

```
SAGE/
├── core/                    # Core infrastructure
│   ├── event_bus.py        # Inter-module communication
│   ├── plugin_manager.py   # Dynamic module loading
│   ├── config_manager.py   # Configuration management
│   ├── resource_monitor.py # System resource monitoring
│   ├── cache_manager.py    # Centralized caching
│   └── logger.py          # Logging system
├── modules/                # Modular components
│   ├── voice/             # Speech recognition & synthesis
│   ├── nlp/               # Natural language processing
│   ├── vision/            # Computer vision
│   ├── calendar/          # Scheduling and reminders
│   ├── web_tools/         # Web integration
│   ├── integrations/      # Office and system integration
│   ├── learning/          # Adaptive learning system
│   ├── fabrication/       # 3D printing and CAD
│   └── custom_skills/     # User-defined skills
├── data/                  # Data storage
│   ├── models/           # AI models cache
│   ├── user_data/        # User preferences and data
│   ├── cache/            # System cache
│   └── logs/             # Application logs
├── config.yaml           # Main configuration
└── main.py              # Application entry point
```

## 🔧 Configuration

### Core Settings (`config.yaml`)

```yaml
# Performance
performance:
  max_memory_mb: 1000      # RAM limit
  max_cpu_percent: 80      # CPU usage limit
  cache_size_mb: 200       # Cache size

# Voice
voice:
  recognition:
    engine: whisper        # whisper, google, vosk
    model: tiny           # tiny, base, small
  synthesis:
    engine: pyttsx3       # pyttsx3, edge-tts
    rate: 200
  wake_word:
    enabled: true
    keyword: sage

# AI
nlp:
  llm:
    provider: ollama      # ollama, gpt4all
    model: phi3:mini      # phi3:mini, llama3.2:1b
    temperature: 0.7
```

### Module-Specific Configuration

Each module has its own config file in `modules/[module]/[module]_config.yaml`:

- `modules/voice/voice_config.yaml` - Voice settings
- `modules/nlp/nlp_config.yaml` - AI and NLP settings  
- `modules/vision/vision_config.yaml` - Computer vision settings

## 🎮 Usage Examples

### Voice Commands
- "Sage, what's the weather today?"
- "Set a reminder for 3pm tomorrow"
- "Search for Python tutorials"
- "Open my Excel file and show me the summary"

### Programmatic API
```python
from modules.voice import VoiceModule
from modules.nlp import NLPModule

# Initialize modules
voice = VoiceModule()
nlp = NLPModule()

# Speak something
await voice.speak("Hello, I'm SAGE!")

# Process text
response = await nlp.process_text("What's the weather like?")
```

## 🧪 Free Technology Stack

### Core Technologies (100% Free)
- **Python 3.8+**: Main programming language
- **asyncio**: Asynchronous programming
- **SQLite**: Local database storage
- **PyQt5**: GUI framework (fallback: tkinter)

### AI & ML (100% Free)
- **Ollama**: Local LLM runtime (Phi3, Llama, Mistral)
- **Whisper**: OpenAI's speech recognition (local)
- **spaCy**: Natural language processing
- **YOLOv8**: Object detection (local inference)
- **face_recognition**: Face detection and recognition

### Voice (100% Free)
- **SpeechRecognition**: Google Speech API (free tier)
- **pyttsx3**: Offline text-to-speech
- **Porcupine**: Wake word detection (free tier)
- **WebRTC VAD**: Voice activity detection

### Web & APIs (Free Tiers)
- **DuckDuckGo Search**: No API key required
- **OpenWeatherMap**: 1000 calls/day free
- **NewsAPI**: 500 requests/day free
- **BeautifulSoup**: Web scraping

## 🏗️ Development

### Adding New Modules

1. **Create Module Structure**:
```bash
mkdir modules/my_module
touch modules/my_module/__init__.py
touch modules/my_module/my_module_config.yaml
```

2. **Implement BaseModule**:
```python
from modules import BaseModule, EventType

class MyModule(BaseModule):
    async def initialize(self) -> bool:
        # Initialize your module
        return True
    
    async def shutdown(self) -> None:
        # Clean up resources
        pass
    
    async def handle_event(self, event) -> None:
        # Handle events from other modules
        pass
```

3. **Register Events**:
```python
self.subscribed_events = [
    EventType.VOICE_COMMAND,
    EventType.CUSTOM_EVENT
]
```

### Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v --cov=modules

# Run specific module tests
pytest tests/unit/test_voice.py
```

### Code Quality

```bash
# Format code
black modules/

# Lint code  
flake8 modules/

# Type checking
mypy modules/
```

## 📊 Performance Monitoring

SAGE includes built-in performance monitoring:

- **Resource Usage**: CPU, memory, disk monitoring
- **Module Performance**: Individual module resource tracking
- **Cache Statistics**: Cache hit rates and memory usage
- **Event Bus Metrics**: Event processing statistics

View real-time stats:
```bash
python main.py --status
```

## 🔒 Privacy & Security

- **Local First**: All core processing happens locally
- **No Telemetry**: No data sent to external servers
- **Sandboxed Modules**: Modules run in isolated environments
- **Configurable Permissions**: Control file and network access
- **Open Source**: Full transparency in code and data handling

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd SAGE

# Setup development environment
python scripts/setup.py
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## 📚 Documentation

- **[API Documentation](docs/API.md)**: Complete API reference
- **[Module Guide](docs/MODULES.md)**: Guide to built-in modules
- **[Free Alternatives](docs/FREE_ALTERNATIVES.md)**: Complete list of free technologies used

## 🐛 Troubleshooting

### Common Issues

1. **Microphone not working**: Check audio device settings in `config.yaml`
2. **Whisper model download fails**: Run `python -c "import whisper; whisper.load_model('tiny')"`
3. **Ollama connection issues**: Ensure Ollama is installed and running
4. **High memory usage**: Reduce cache size or model sizes in config

### Performance Optimization

- Use smaller AI models (tiny/base instead of large)
- Enable lazy loading for optional modules
- Adjust cache sizes based on available RAM
- Monitor resource usage with `python main.py --status`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI**: For Whisper speech recognition
- **Meta**: For Llama models
- **Microsoft**: For Phi3 models  
- **Anthropic**: For inspiration and AI assistance
- **Open Source Community**: For all the amazing free tools

---

**SAGE** - Smart, Adaptive, General, Executive - Your zero-cost AI companion! 🤖✨