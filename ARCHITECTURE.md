# SAGE Architecture Documentation

## Overview
SAGE (Smart Adaptive General Executive) is a voice-controlled AI assistant with modular architecture, conversational state management, and multi-modal interaction capabilities.

---

## 📁 **Directory Structure**

```
SAGE/
├── main.py                          # Main application entry point
├── demo_sage.py                     # Interactive demo interface
├── config.yaml                      # Main configuration file
├── requirements.txt                 # Python dependencies
├── ARCHITECTURE.md                  # This documentation file
├── 
├── 📁 core/                         # Core system components
│   ├── __init__.py
│   ├── logger.py                    # Centralized logging system
│   ├── config_manager.py            # Configuration management
│   ├── event_bus.py                 # Event-driven communication system
│   ├── plugin_manager.py            # Module loading and management
│   ├── base_module.py               # Base class for all modules
│   ├── resource_monitor.py          # System resource monitoring
│   └── cache_manager.py             # Caching system for performance
│
├── 📁 modules/                      # Feature modules (plugins)
│   ├── __init__.py
│   │
│   ├── 📁 voice/                    # Voice processing system
│   │   ├── __init__.py              # Voice module interface
│   │   ├── voice_config.yaml        # Voice-specific configuration
│   │   ├── synthesis.py             # Text-to-Speech (TTS) engine
│   │   ├── enhanced_recognition.py  # Speech-to-Text (STT) engine
│   │   ├── enhanced_voice_module.py # Enhanced voice processing
│   │   ├── conversation_state.py    # Conversation state management
│   │   ├── wake_word.py             # Wake word detection
│   │   └── audio_utils.py           # Audio processing utilities
│   │
│   ├── 📁 nlp/                      # Natural Language Processing
│   │   ├── __init__.py              # NLP module interface
│   │   ├── nlp_module.py            # Main NLP processing
│   │   ├── intent_recognition.py    # Intent analysis and classification
│   │   ├── conversation_memory.py   # Conversation context memory
│   │   └── response_generation.py   # Response generation logic
│   │
│   └── 📁 calendar/                 # Calendar and scheduling
│       ├── __init__.py              # Calendar module interface
│       ├── calendar_module.py       # Main calendar functionality
│       ├── simplified_calendar.py   # Simplified calendar implementation
│       └── natural_language_parser.py # Calendar command parsing
│
├── 📁 data/                         # Data storage
│   ├── calendar.db                  # SQLite calendar database
│   ├── conversations/               # Conversation history
│   └── cache/                       # Cached data files
│
├── 📁 logs/                         # Application logs
│   ├── sage.log                     # Main application log
│   ├── voice.log                    # Voice processing logs
│   └── error.log                    # Error-specific logs
│
└── 📁 tests/                        # Test files
    ├── test_voice.py
    ├── test_calendar.py
    └── test_nlp.py
```

---

## 🏗️ **Core System Components**

### **main.py** - Application Entry Point
**Purpose**: Main application orchestrator and voice command processor
**Key Functions**:
- `SAGEApplication.__init__()` - Initialize core components
- `SAGEApplication.initialize()` - Start all modules and services
- `SAGEApplication._process_voice_commands()` - Main voice processing loop
- `SAGEApplication._handle_conversation_action()` - Process conversation state actions
- `SAGEApplication._execute_confirmed_command()` - Execute user-confirmed commands
- `SAGEApplication._speak_and_manage_audio()` - Manage TTS and audio resources

### **demo_sage.py** - Interactive Interface
**Purpose**: Text-based interactive interface for testing without voice
**Key Functions**:
- `main()` - Interactive command loop
- Text input processing and response display

---

## 🔧 **Core Infrastructure**

### **core/logger.py** - Logging System
**Purpose**: Centralized logging with multiple levels and file outputs
**Key Classes**:
- `Logger` - Main logging coordinator
**Key Functions**:
- `get_logger(name)` - Get named logger instance
- `set_level(level)` - Set global log level
- `flush_logs()` - Force write pending logs

### **core/config_manager.py** - Configuration Management
**Purpose**: Load, validate, and manage application configuration
**Key Classes**:
- `ConfigManager` - Configuration handler
**Key Functions**:
- `load_config()` - Load configuration from YAML
- `validate_config()` - Validate configuration integrity
- `get(key, default)` - Get configuration value with fallback

### **core/event_bus.py** - Event System
**Purpose**: Event-driven communication between modules
**Key Classes**:
- `EventBus` - Central event coordinator
- `Event` - Event data structure
- `EventType` - Event type enumeration
**Key Functions**:
- `emit(event_type, data)` - Emit event to subscribers
- `subscribe(event_type, callback)` - Subscribe to event type
- `unsubscribe(event_type, callback)` - Remove subscription

### **core/plugin_manager.py** - Module Management
**Purpose**: Dynamic loading and management of feature modules
**Key Classes**:
- `PluginManager` - Module lifecycle manager
**Key Functions**:
- `load_module(name)` - Load and initialize module
- `unload_module(name)` - Safely unload module
- `get_module(name)` - Get reference to loaded module
- `unload_all_modules()` - Shutdown all modules

### **core/base_module.py** - Module Base Class
**Purpose**: Standard interface and utilities for all modules
**Key Classes**:
- `BaseModule` - Base class for all feature modules
**Key Functions**:
- `initialize()` - Module initialization hook
- `shutdown()` - Module cleanup hook
- `get_status()` - Module health status
- `emit_event()` - Emit events to system

### **core/resource_monitor.py** - System Monitoring
**Purpose**: Monitor system resources (CPU, memory, disk)
**Key Classes**:
- `ResourceMonitor` - Resource tracking system
**Key Functions**:
- `start()` - Begin resource monitoring
- `get_stats()` - Get current resource usage
- `check_thresholds()` - Check for resource warnings

### **core/cache_manager.py** - Caching System
**Purpose**: Performance optimization through intelligent caching
**Key Classes**:
- `CacheManager` - Cache coordinator
**Key Functions**:
- `get(key)` - Retrieve cached value
- `set(key, value, ttl)` - Store value with expiration
- `invalidate(pattern)` - Remove cached entries
- `cleanup()` - Remove expired entries

---

## 🗣️ **Voice Processing System**

### **modules/voice/__init__.py** - Voice Module Interface
**Purpose**: Main voice module coordinator
**Key Classes**:
- `VoiceModule` - Voice system coordinator
**Key Functions**:
- `start_listening()` - Begin voice recognition
- `stop_listening()` - Stop voice recognition
- `speak_text(text)` - Text-to-speech output
- `get_voice_input()` - Get recognized speech

### **modules/voice/conversation_state.py** - Conversation Management
**Purpose**: Manage natural conversation flow and state transitions
**Key Classes**:
- `ConversationManager` - Conversation state controller
- `ConversationState` - State enumeration (SLEEPING, LISTENING, CONFIRMING, EXECUTING)
**Key Functions**:
- `process_voice_input(text, confidence)` - Process input based on current state
- `set_state(new_state, reason)` - Change conversation state
- `request_confirmation(command, data, message)` - Request user confirmation
- `update_interaction()` - Update last interaction timestamp

### **modules/voice/synthesis.py** - Text-to-Speech Engine
**Purpose**: Convert text to spoken audio with multiple TTS backends
**Key Classes**:
- `VoiceSynthesis` - TTS engine coordinator
**Key Functions**:
- `speak(text, config)` - Primary TTS interface
- `_speak_with_free_cloud_tts(text)` - Cloud TTS using gTTS + Windows MediaPlayer
- `_speak_with_fresh_engine(text)` - Fresh pyttsx3 engine approach
- `_apply_emotion_to_text(text, emotion)` - Text modification for emotions

### **modules/voice/enhanced_recognition.py** - Speech Recognition
**Purpose**: Convert spoken audio to text using Whisper and VAD
**Key Classes**:
- `EnhancedVoiceRecognition` - STT engine coordinator
**Key Functions**:
- `start_listening()` - Begin continuous voice recognition
- `stop_listening()` - Stop voice recognition gracefully
- `_audio_processing_loop()` - Main audio capture and processing loop
- `_transcribe_audio(audio_data)` - Convert audio to text using Whisper

### **modules/voice/voice_config.yaml** - Voice Configuration
**Purpose**: Voice-specific settings and parameters
**Key Settings**:
- `energy_threshold: 300` - Audio sensitivity level
- `pause_threshold: 1.5` - Silence detection threshold (seconds)
- `phrase_timeout: 0.6` - Inter-word timeout (seconds)
- `operation_timeout: 5` - Maximum recognition time (seconds)

### **modules/voice/wake_word.py** - Wake Word Detection
**Purpose**: Detect activation phrases ("Hey Sage", "Sage")
**Key Classes**:
- `WakeWordDetector` - Wake word recognition system
**Key Functions**:
- `start_detection()` - Begin wake word monitoring
- `stop_detection()` - Stop wake word detection
- `_process_wake_word(text)` - Validate wake word detection

### **modules/voice/audio_utils.py** - Audio Processing
**Purpose**: Low-level audio processing and Voice Activity Detection
**Key Classes**:
- `AudioProcessor` - Audio signal processing
- `VADProcessor` - Voice Activity Detection
**Key Functions**:
- `process_audio_chunk(audio)` - Process raw audio data
- `detect_voice_activity(audio)` - Determine if audio contains speech
- `apply_noise_gate(audio)` - Remove background noise

---

## 🧠 **Natural Language Processing**

### **modules/nlp/nlp_module.py** - NLP Coordinator
**Purpose**: Main NLP processing and coordination
**Key Classes**:
- `NLPModule` - NLP system coordinator
**Key Functions**:
- `analyze_intent(text)` - Determine user intent from text
- `process_text(text)` - Full NLP processing pipeline
- `generate_response(context)` - Generate contextual responses

### **modules/nlp/intent_recognition.py** - Intent Analysis
**Purpose**: Classify user intentions from natural language
**Key Classes**:
- `IntentRecognizer` - Intent classification engine
**Key Functions**:
- `classify_intent(text)` - Determine primary intent
- `extract_entities(text)` - Extract named entities
- `get_confidence_score(text, intent)` - Confidence measurement

**Intent Categories**:
- `time_query` - Time/clock requests
- `check_calendar` - Calendar viewing requests
- `modify_meeting` - Calendar modification requests
- `greeting` - Greeting and social interactions
- `help_request` - Help and assistance requests
- `question` - General questions
- `conversation` - Open-ended conversation

### **modules/nlp/conversation_memory.py** - Context Memory
**Purpose**: Maintain conversation context and history
**Key Classes**:
- `ConversationMemory` - Context management system
**Key Functions**:
- `add_interaction(user_input, assistant_response)` - Store interaction
- `get_context(depth)` - Retrieve conversation history
- `clear_context()` - Reset conversation memory

### **modules/nlp/response_generation.py** - Response Creation
**Purpose**: Generate appropriate responses based on context
**Key Classes**:
- `ResponseGenerator` - Response creation system
**Key Functions**:
- `generate_response(intent, entities, context)` - Create contextual response
- `apply_personality(response)` - Add personality traits
- `format_for_speech(response)` - Optimize for TTS

---

## 📅 **Calendar System**

### **modules/calendar/calendar_module.py** - Calendar Coordinator
**Purpose**: Main calendar functionality and event management
**Key Classes**:
- `CalendarModule` - Calendar system coordinator
- `CalendarEvent` - Event data structure
**Key Functions**:
- `handle_natural_language(text)` - Process calendar commands
- `create_event(title, datetime, duration)` - Create new calendar event
- `list_events(start_date, end_date)` - Retrieve events in date range
- `_handle_calendar_request(text, intent)` - Process calendar queries

### **modules/calendar/simplified_calendar.py** - Simplified Calendar
**Purpose**: Lightweight calendar implementation
**Key Classes**:
- `SimplifiedCalendarModule` - Simplified calendar system
**Key Functions**:
- `_handle_calendar_query(text)` - Process calendar questions
- `_parse_date_time(text)` - Extract dates and times from text

### **modules/calendar/natural_language_parser.py** - Command Parsing
**Purpose**: Parse natural language calendar commands
**Key Classes**:
- `NaturalLanguageParser` - Calendar command parser
**Key Functions**:
- `parse_datetime(text)` - Extract date/time from text
- `parse_duration(text)` - Extract duration information
- `parse_event_details(text)` - Extract event details

---

## 🔄 **Data Flow Architecture**

### **Voice Command Processing Flow**:
```
1. Audio Input → Enhanced Recognition (Whisper)
2. Text Output → Conversation State Manager
3. State Analysis → Intent Recognition (NLP)
4. Intent → Command Router (main.py)
5. Command → Module Handler (Calendar/NLP/etc.)
6. Response → Text-to-Speech (gTTS/pyttsx3)
7. Audio Output → Voice Module
8. State Update → Conversation Manager
```

### **Conversation State Flow**:
```
SLEEPING (requires wake word)
    ↓ "Hey Sage"
LISTENING (active conversation)
    ↓ Action command
CONFIRMING (waiting for yes/no)
    ↓ "Yes"/"No"
EXECUTING (processing command)
    ↓ Command complete
LISTENING (ready for next command)
    ↓ 30s timeout
SLEEPING (back to wake word mode)
```

### **Event System Flow**:
```
Module A → Event Bus → Module B
         ↓
    Event Logging → Logger → Log Files
         ↓
    Resource Monitor → Performance Tracking
```

---

## ⚙️ **Configuration System**

### **config.yaml** - Main Configuration
**Key Sections**:
- `core.log_level` - Global logging level
- `voice.recognition.engine` - STT engine selection
- `voice.synthesis.engine` - TTS engine selection
- `nlp.model_path` - NLP model location
- `calendar.db_path` - Calendar database location

### **modules/voice/voice_config.yaml** - Voice Settings
**Key Parameters**:
- `energy_threshold` - Microphone sensitivity
- `pause_threshold` - Silence detection time
- `phrase_timeout` - Word-to-word timeout
- `vad_enabled` - Voice Activity Detection toggle
- `vad_aggressiveness` - VAD sensitivity (0-3)

---

## 🎯 **Key Integration Points**

### **LLM vs Rule-Based Processing**:

**Intent Recognition**: Hybrid approach using NLP models for intent classification

**Command Routing**: Traditional if/else logic based on detected intent:
```python
if intent in ['time', 'clock', 'current_time', 'time_query']:
    # Handle time queries with hardcoded logic
elif intent in ['check_calendar', 'modify_meeting']:
    # Route to calendar module
elif intent in ['question', 'conversation', 'general']:
    # Use LLM through NLP module for open-ended responses
```

**Response Generation**: 
- **Simple Commands**: Hardcoded responses (time, calendar confirmations)
- **Complex Queries**: LLM-generated responses via NLP module
- **Conversational**: Full LLM processing for natural dialogue

### **Audio Resource Management**:
The system uses careful audio resource management to prevent conflicts:

1. **Stop Listening** before TTS output
2. **Wait for TTS completion** before restarting recognition
3. **Voice Activity Detection** to prevent self-hearing
4. **Cloud TTS** to bypass Windows audio driver contamination

### **State Persistence**:
- **Conversation State**: Maintained in memory with timeout management
- **Calendar Data**: Persisted in SQLite database
- **Configuration**: YAML files with runtime reloading
- **Logs**: File-based with rotation and retention policies

---

## 🚀 **Performance Optimizations**

### **Caching Strategy**:
- **TTS Audio**: Cache generated speech for repeated phrases
- **Intent Recognition**: Cache common command patterns
- **Calendar Queries**: Cache frequent date/time calculations

### **Resource Monitoring**:
- **Memory Usage**: Track module memory consumption
- **CPU Usage**: Monitor processing load
- **Audio Latency**: Measure recognition and synthesis delays

### **Async Architecture**:
- **Non-blocking Voice Recognition**: Continuous background processing
- **Concurrent Module Operations**: Parallel command processing
- **Event-Driven Communication**: Loose coupling between components

---

## 🔧 **Development and Extension**

### **Adding New Modules**:
1. Inherit from `BaseModule` in `core/base_module.py`
2. Implement required methods: `initialize()`, `shutdown()`, `get_status()`
3. Register module in `core/plugin_manager.py`
4. Add configuration section to `config.yaml`

### **Adding New Intents**:
1. Update intent recognition in `modules/nlp/intent_recognition.py`
2. Add routing logic in `main.py` command router
3. Implement handler in appropriate module
4. Add confirmation logic if needed

### **Adding New Voice Commands**:
1. Define intent in NLP module
2. Add command routing in `main.py`
3. Implement command handler
4. Add confirmation message generation
5. Test conversation flow

---

This architecture provides a modular, extensible foundation for a sophisticated voice-controlled AI assistant with natural conversation capabilities, robust error handling, and performance optimization.