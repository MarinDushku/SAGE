#!/usr/bin/env python3
"""
Script to create GitHub issues for SAGE development milestones
Run this script after installing GitHub CLI and authenticating
"""

import subprocess
import sys
from typing import List, Dict

class GitHubIssueCreator:
    """Creates GitHub issues for SAGE development"""
    
    def __init__(self, repo: str = "MarinDushku/SAGE"):
        self.repo = repo
        self.issues = self._define_issues()
        
    def _define_issues(self) -> List[Dict]:
        """Define all GitHub issues with details"""
        return [
            # Milestone 1: Core Infrastructure (Week 1)
            {
                "title": "Project setup and structure",
                "body": """## 📋 Issue Description
Complete project setup and structure for SAGE - Smart Adaptive General Executive.

## ✅ Completed Tasks
- [x] Create folder structure
- [x] Set up requirements.txt with zero-cost dependencies  
- [x] Configure git repository
- [x] Create README.md with comprehensive documentation
- [x] Set up LICENSE and .gitignore
- [x] Create main.py entry point
- [x] Implement core module structure

## 🎯 Remaining Tasks
- [ ] Verify setup script works on all platforms
- [ ] Add missing __init__.py files if needed
- [ ] Test virtual environment creation

## 🔧 Technical Requirements
- Complete modular folder structure
- All dependencies are free/open-source
- Proper git configuration
- Cross-platform compatibility

## 📊 Acceptance Criteria
- [x] Folder structure matches specification
- [x] Requirements include only free technologies
- [x] Git repository properly configured
- [x] Documentation is comprehensive

**Status: ✅ COMPLETED**

## 🏷️ Labels
core, priority:high, cost:free

## 📅 Milestone
Core Infrastructure (Week 1)""",
                "labels": ["core", "priority:high", "cost:free", "status:completed"]
            },
            
            {
                "title": "Event bus system",
                "body": """## 📋 Issue Description
Implement async event bus system for inter-module communication in SAGE.

## ✅ Completed Tasks
- [x] Basic async event bus implementation
- [x] Event type definitions with enum
- [x] Event data structures with dataclasses
- [x] Subscriber management system
- [x] Event processing loop with error handling

## 🎯 Remaining Tasks
- [ ] Add event priority handling system
- [ ] Implement event filtering and routing
- [ ] Add event persistence for critical events
- [ ] Performance optimization for high-frequency events
- [ ] Add comprehensive unit tests

## 🔧 Technical Requirements
- Async event processing with asyncio
- Type-safe event definitions
- Error handling and recovery
- Performance monitoring
- Memory efficient queue management

## 📊 Acceptance Criteria
- [x] Basic event bus functional
- [ ] Can handle 1000+ events/second
- [ ] Memory usage under 50MB under load
- [ ] All events properly typed
- [ ] Test coverage >90%

**Status: 🟡 IN PROGRESS (Core complete, optimizations needed)**

## 🏷️ Labels
core, priority:high, cost:free

## 📅 Milestone  
Core Infrastructure (Week 1)""",
                "labels": ["core", "priority:high", "cost:free"]
            },
            
            {
                "title": "Plugin manager", 
                "body": """## 📋 Issue Description
Implement dynamic module loading and management system for SAGE.

## ✅ Completed Tasks
- [x] Basic plugin manager implementation
- [x] Dynamic module discovery and loading
- [x] Module lifecycle management (load/unload)
- [x] Dependency injection for core services
- [x] Module status tracking

## 🎯 Remaining Tasks
- [ ] Implement dependency resolution between modules
- [ ] Add hot reload capability for development
- [ ] Module sandboxing and security
- [ ] Plugin validation and verification
- [ ] Add comprehensive unit tests

## 🔧 Technical Requirements
- Dynamic module loading with importlib
- Dependency resolution graph
- Hot reload without service interruption
- Security sandboxing
- Module resource isolation

## 📊 Acceptance Criteria
- [x] Basic module loading works
- [ ] Dependency resolution functional
- [ ] Hot reload works reliably
- [ ] Security sandbox active
- [ ] Test coverage >90%

**Status: 🟡 IN PROGRESS (Core complete, advanced features needed)**

## 🏷️ Labels
core, priority:high, cost:free

## 📅 Milestone
Core Infrastructure (Week 1)""",
                "labels": ["core", "priority:high", "cost:free"]
            },
            
            {
                "title": "Resource monitor",
                "body": """## 📋 Issue Description
Implement system resource monitoring and performance optimization for SAGE.

## ✅ Completed Tasks
- [x] Basic resource monitor implementation
- [x] CPU and memory tracking with psutil
- [x] Resource snapshot data structures
- [x] Threshold-based alerting system
- [x] Historical data collection

## 🎯 Remaining Tasks
- [ ] Add per-module resource tracking
- [ ] Implement resource limits enforcement
- [ ] Performance profiling integration
- [ ] Resource usage optimization suggestions
- [ ] Add comprehensive unit tests

## 🔧 Technical Requirements
- Real-time resource monitoring
- Per-module resource attribution
- Configurable thresholds and limits
- Performance profiling hooks
- Resource optimization automation

## 📊 Acceptance Criteria
- [x] Basic monitoring functional
- [ ] Per-module tracking works
- [ ] Resource limits enforced
- [ ] Profiling data collected
- [ ] Test coverage >80%

**Status: 🟡 IN PROGRESS (Core complete, advanced features needed)**

## 🏷️ Labels
core, optimization:cpu, cost:free

## 📅 Milestone
Core Infrastructure (Week 1)""",
                "labels": ["core", "optimization:cpu", "cost:free"]
            },
            
            {
                "title": "Cache manager",
                "body": """## 📋 Issue Description
Implement centralized caching system with LRU eviction and persistence for SAGE.

## ✅ Completed Tasks
- [x] LRU cache implementation with OrderedDict
- [x] Persistent cache storage with pickle
- [x] Cache invalidation system
- [x] Memory usage tracking and limits
- [x] TTL (time-to-live) support

## 🎯 Remaining Tasks
- [ ] Add cache statistics and monitoring
- [ ] Implement cache warming strategies
- [ ] Add compression for large cache entries
- [ ] Cache synchronization between instances
- [ ] Add comprehensive unit tests

## 🔧 Technical Requirements
- LRU eviction policy
- Persistent storage backend
- Configurable memory limits
- Thread-safe operations
- Performance monitoring

## 📊 Acceptance Criteria
- [x] LRU cache works correctly
- [x] Persistent storage functional
- [x] Memory limits respected
- [ ] Cache hit rate >80% for typical usage
- [ ] Test coverage >90%

**Status: ✅ COMPLETED (Core functionality ready)**

## 🏷️ Labels
core, optimization:memory, cost:free

## 📅 Milestone
Core Infrastructure (Week 1)""",
                "labels": ["core", "optimization:memory", "cost:free", "status:completed"]
            },
            
            # Milestone 2: Voice Module (Week 2-3)
            {
                "title": "Voice recognition setup",
                "body": """## 📋 Issue Description
Implement speech recognition system using free technologies for SAGE voice interface.

## 🎯 Tasks
- [ ] Integrate SpeechRecognition library
- [ ] Set up Whisper model integration (local)
- [ ] Implement audio streaming and processing
- [ ] Add voice activity detection (VAD)
- [ ] Create audio input configuration
- [ ] Add noise reduction and filtering

## 🔧 Technical Requirements
- Multiple recognition engines (Whisper, Google, Vosk)
- Local model inference for offline capability
- Real-time audio streaming
- Voice activity detection
- Configurable audio parameters

## 📊 Acceptance Criteria
- [ ] Whisper integration works offline
- [ ] Google Speech API works (free tier)
- [ ] Vosk offline recognition functional
- [ ] VAD reduces false activations
- [ ] Recognition accuracy >85%
- [ ] Response time <2 seconds

## 🏷️ Labels
module:voice, priority:high, cost:free

## 📅 Milestone
Voice Module (Week 2-3)""",
                "labels": ["module:voice", "priority:high", "cost:free"]
            },
            
            {
                "title": "Offline TTS (Text-to-Speech)",
                "body": """## 📋 Issue Description
Implement offline text-to-speech system using free technologies for SAGE voice output.

## 🎯 Tasks
- [ ] Set up pyttsx3 offline TTS engine
- [ ] Integrate edge-tts (Microsoft free TTS)
- [ ] Implement voice selection and configuration
- [ ] Add speech rate and pitch control
- [ ] Create voice queue management
- [ ] Add SSML support for advanced speech control

## 🔧 Technical Requirements
- Offline TTS capability (pyttsx3)
- Online TTS fallback (edge-tts)
- Voice customization options
- Speech queue and interruption handling
- Cross-platform compatibility

## 📊 Acceptance Criteria
- [ ] pyttsx3 works offline on all platforms
- [ ] edge-tts provides high-quality voices
- [ ] Voice selection menu functional
- [ ] Speech rate/pitch controls work
- [ ] Queue management prevents overlapping
- [ ] Speech sounds natural and clear

## 🏷️ Labels
module:voice, priority:high, cost:free

## 📅 Milestone
Voice Module (Week 2-3)""",
                "labels": ["module:voice", "priority:high", "cost:free"]
            },
            
            {
                "title": "Wake word detection",
                "body": """## 📋 Issue Description
Implement wake word detection system for hands-free SAGE activation.

## 🎯 Tasks
- [ ] Integrate Porcupine wake word detection (free tier)
- [ ] Set up Snowboy as alternative (deprecated but works)
- [ ] Implement custom wake word training
- [ ] Add background listening with low CPU usage
- [ ] Create sensitivity adjustment controls
- [ ] Add multiple wake word support

## 🔧 Technical Requirements
- Always-on background listening
- Low CPU/memory usage (<5% CPU)
- Configurable sensitivity levels
- Custom wake word training
- Multiple engine support

## 📊 Acceptance Criteria
- [ ] Porcupine integration works (3 free keywords)
- [ ] Snowboy fallback functional
- [ ] Wake word detection accuracy >90%
- [ ] Background CPU usage <5%
- [ ] False positive rate <1%
- [ ] Custom training works

## 🏷️ Labels
module:voice, priority:medium, cost:free

## 📅 Milestone
Voice Module (Week 2-3)""",
                "labels": ["module:voice", "priority:medium", "cost:free"]
            },
            
            {
                "title": "Voice command parser",
                "body": """## 📋 Issue Description
Implement voice command parsing and intent extraction for SAGE voice interface.

## 🎯 Tasks
- [ ] Define command grammar and patterns
- [ ] Implement intent extraction algorithms
- [ ] Add confidence scoring for commands
- [ ] Create command validation system
- [ ] Add support for parameters and entities
- [ ] Implement command shortcuts and aliases

## 🔧 Technical Requirements
- Grammar-based command parsing
- Intent classification with confidence scores
- Entity extraction (dates, numbers, names)
- Command validation and sanitization
- Extensible command registry

## 📊 Acceptance Criteria
- [ ] Command grammar covers common use cases
- [ ] Intent extraction accuracy >85%
- [ ] Confidence scoring works reliably
- [ ] Parameter extraction functional
- [ ] Command shortcuts work
- [ ] Easy to add new commands

## 🏷️ Labels
module:voice, module:nlp, cost:free

## 📅 Milestone
Voice Module (Week 2-3)""",
                "labels": ["module:voice", "module:nlp", "cost:free"]
            },
            
            # Milestone 3: Local AI Integration (Week 4-5)
            {
                "title": "Ollama setup and integration",
                "body": """## 📋 Issue Description
Set up Ollama for local LLM inference and model management in SAGE.

## 🎯 Tasks
- [ ] Install and configure Ollama service
- [ ] Download recommended models (phi3:mini, llama3.2:1b)
- [ ] Implement model management system
- [ ] Add model switching capabilities
- [ ] Create model performance monitoring
- [ ] Set up model auto-update system

## 🔧 Technical Requirements
- Ollama service integration
- Model lifecycle management
- Performance monitoring
- Resource usage optimization
- Model versioning and updates

## 📊 Acceptance Criteria
- [ ] Ollama service runs reliably
- [ ] Models download and load correctly
- [ ] Model switching works seamlessly
- [ ] Performance metrics collected
- [ ] Memory usage optimized
- [ ] Auto-updates work safely

## 🏷️ Labels
module:nlp, priority:high, cost:free

## 📅 Milestone
Local AI Integration (Week 4-5)""",
                "labels": ["module:nlp", "priority:high", "cost:free"]
            },
            
            {
                "title": "LLM interface and conversation management",
                "body": """## 📋 Issue Description
Implement LLM interface with conversation management and context optimization for SAGE.

## 🎯 Tasks
- [ ] Create LLM interface abstraction
- [ ] Implement conversation history management
- [ ] Add context window optimization
- [ ] Set up response streaming
- [ ] Create conversation persistence
- [ ] Add multi-turn conversation support

## 🔧 Technical Requirements
- Provider-agnostic LLM interface
- Context window management
- Conversation state persistence
- Streaming response handling
- Memory-efficient context storage

## 📊 Acceptance Criteria
- [ ] LLM interface works with multiple providers
- [ ] Conversation history maintained correctly
- [ ] Context optimization reduces token usage
- [ ] Response streaming works smoothly
- [ ] Multi-turn conversations flow naturally
- [ ] Memory usage stays reasonable

## 🏷️ Labels
module:nlp, priority:high, cost:free

## 📅 Milestone
Local AI Integration (Week 4-5)""",
                "labels": ["module:nlp", "priority:high", "cost:free"]
            },
            
            {
                "title": "Prompt engineering and optimization",
                "body": """## 📋 Issue Description
Implement prompt engineering system for optimal LLM interactions in SAGE.

## 🎯 Tasks
- [ ] Create system prompt templates
- [ ] Implement few-shot example management
- [ ] Add response format optimization
- [ ] Create prompt versioning system
- [ ] Add prompt performance analytics
- [ ] Implement dynamic prompt adaptation

## 🔧 Technical Requirements
- Template-based prompt system
- Few-shot example library
- Response format control
- Prompt A/B testing capability
- Performance metrics collection

## 📊 Acceptance Criteria
- [ ] System prompts improve response quality
- [ ] Few-shot examples enhance accuracy
- [ ] Response formats are consistent
- [ ] Prompt versioning works
- [ ] Performance metrics show improvement
- [ ] Dynamic adaptation reduces errors

## 🏷️ Labels
module:nlp, optimization:quality, cost:free

## 📅 Milestone
Local AI Integration (Week 4-5)""",
                "labels": ["module:nlp", "optimization:quality", "cost:free"]
            },
            
            {
                "title": "LLM response caching system",
                "body": """## 📋 Issue Description
Implement intelligent caching system for LLM responses to improve performance and reduce compute costs.

## 🎯 Tasks
- [ ] Cache LLM responses by input hash
- [ ] Implement semantic similarity matching
- [ ] Add cache invalidation rules
- [ ] Create cache performance monitoring
- [ ] Add cache compression for storage efficiency
- [ ] Implement cache warming strategies

## 🔧 Technical Requirements
- Semantic similarity search
- Efficient cache storage
- Smart invalidation policies
- Performance monitoring
- Storage optimization

## 📊 Acceptance Criteria
- [ ] Cache hit rate >60% for common queries
- [ ] Semantic matching works accurately
- [ ] Cache invalidation prevents stale responses
- [ ] Storage usage optimized
- [ ] Performance monitoring functional
- [ ] Cache warming improves cold start

## 🏷️ Labels
module:nlp, optimization:cpu, cost:free

## 📅 Milestone
Local AI Integration (Week 4-5)""",
                "labels": ["module:nlp", "optimization:cpu", "cost:free"]
            }
        ]
    
    def create_issue(self, issue: Dict) -> bool:
        """Create a single GitHub issue"""
        try:
            cmd = [
                "gh", "issue", "create",
                "--title", issue["title"],
                "--body", issue["body"],
                "--label", ",".join(issue["labels"])
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Created issue: {issue['title']}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create issue '{issue['title']}': {e}")
            print(f"Error output: {e.stderr}")
            return False
            
    def create_all_issues(self) -> None:
        """Create all GitHub issues"""
        print("🚀 Creating GitHub issues for SAGE development...")
        print(f"Repository: {self.repo}")
        print(f"Total issues to create: {len(self.issues)}")
        print()
        
        success_count = 0
        
        for i, issue in enumerate(self.issues, 1):
            print(f"Creating issue {i}/{len(self.issues)}: {issue['title']}")
            if self.create_issue(issue):
                success_count += 1
            print()
            
        print(f"✅ Successfully created {success_count}/{len(self.issues)} issues")
        
        if success_count < len(self.issues):
            print("⚠️  Some issues failed to create. Check the error messages above.")
            
    def check_gh_cli(self) -> bool:
        """Check if GitHub CLI is installed and authenticated"""
        try:
            # Check if gh is installed
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
            
            # Check if authenticated
            result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ GitHub CLI not authenticated. Please run: gh auth login")
                return False
                
            print("✅ GitHub CLI is installed and authenticated")
            return True
            
        except subprocess.CalledProcessError:
            print("❌ GitHub CLI not found. Please install it first:")
            print("   https://cli.github.com/")
            return False
            
    def print_manual_instructions(self) -> None:
        """Print manual instructions if CLI creation fails"""
        print("\n" + "="*60)
        print("📝 MANUAL ISSUE CREATION INSTRUCTIONS")
        print("="*60)
        print("\nIf automated creation fails, create these issues manually on GitHub:")
        print(f"Repository: https://github.com/{self.repo}/issues/new")
        print()
        
        for i, issue in enumerate(self.issues, 1):
            print(f"Issue #{i}: {issue['title']}")
            print(f"Labels: {', '.join(issue['labels'])}")
            print("Body:")
            print(issue['body'][:200] + "..." if len(issue['body']) > 200 else issue['body'])
            print("-" * 40)


def main():
    """Main function"""
    creator = GitHubIssueCreator()
    
    if not creator.check_gh_cli():
        print("\n🔧 Please install and authenticate GitHub CLI, then run this script again.")
        print("\nInstallation instructions:")
        print("1. Install GitHub CLI: https://cli.github.com/")
        print("2. Authenticate: gh auth login")
        print("3. Run this script: python scripts/create_github_issues.py")
        
        # Provide manual instructions as fallback
        creator.print_manual_instructions()
        return 1
        
    creator.create_all_issues()
    return 0


if __name__ == "__main__":
    exit(main())