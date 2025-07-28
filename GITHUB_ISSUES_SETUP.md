# GitHub Issues Setup for SAGE

## 🎯 Overview
This document explains how to set up the GitHub issues for SAGE development milestones.

## 🚀 Quick Setup (Automated)

### Prerequisites
1. Install GitHub CLI:
   ```bash
   # On Ubuntu/Debian
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
   sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt update && sudo apt install gh
   
   # On macOS
   brew install gh
   
   # On Windows
   winget install --id GitHub.cli
   ```

2. Authenticate with GitHub:
   ```bash
   gh auth login
   ```

### Create All Issues Automatically
```bash
cd SAGE
python scripts/create_github_issues.py
```

## 📋 Manual Setup (Alternative)

If the automated script doesn't work, create these issues manually at:
https://github.com/MarinDushku/SAGE/issues/new

## 🏗️ Issue Structure

### Milestone 1: Core Infrastructure (Week 1)

#### Issue #1: Project setup and structure ✅ COMPLETED
- **Labels**: `core`, `priority:high`, `cost:free`, `completed`
- **Status**: All basic project structure is complete
- **Tasks**: Folder structure, requirements.txt, git setup, README

#### Issue #2: Event bus system 🟡 IN PROGRESS  
- **Labels**: `core`, `priority:high`, `cost:free`
- **Status**: Core implementation done, optimizations needed
- **Tasks**: Priority handling, filtering, persistence, performance optimization

#### Issue #3: Plugin manager 🟡 IN PROGRESS
- **Labels**: `core`, `priority:high`, `cost:free`  
- **Status**: Basic loading works, advanced features needed
- **Tasks**: Dependency resolution, hot reload, sandboxing

#### Issue #4: Resource monitor 🟡 IN PROGRESS
- **Labels**: `core`, `optimization:cpu`, `cost:free`
- **Status**: Basic monitoring works, per-module tracking needed
- **Tasks**: Per-module tracking, limits enforcement, profiling

#### Issue #5: Cache manager ✅ COMPLETED
- **Labels**: `core`, `optimization:memory`, `cost:free`, `completed`
- **Status**: Core functionality ready
- **Tasks**: LRU cache, persistence, TTL support

### Milestone 2: Voice Module (Week 2-3)

#### Issue #6: Voice recognition setup
- **Labels**: `module:voice`, `priority:high`, `cost:free`
- **Tasks**: Whisper integration, audio streaming, VAD

#### Issue #7: Offline TTS
- **Labels**: `module:voice`, `priority:high`, `cost:free`
- **Tasks**: pyttsx3 setup, voice selection, speech controls

#### Issue #8: Wake word detection  
- **Labels**: `module:voice`, `priority:medium`, `cost:free`
- **Tasks**: Porcupine integration, background listening

#### Issue #9: Voice command parser
- **Labels**: `module:voice`, `module:nlp`, `cost:free`
- **Tasks**: Command grammar, intent extraction, confidence scoring

### Milestone 3: Local AI Integration (Week 4-5)

#### Issue #10: Ollama setup
- **Labels**: `module:nlp`, `priority:high`, `cost:free`
- **Tasks**: Ollama installation, model management

#### Issue #11: LLM interface
- **Labels**: `module:nlp`, `priority:high`, `cost:free`
- **Tasks**: Conversation management, context optimization, streaming

#### Issue #12: Prompt engineering
- **Labels**: `module:nlp`, `optimization:quality`, `cost:free`
- **Tasks**: System prompts, few-shot examples, response formatting

#### Issue #13: Response caching
- **Labels**: `module:nlp`, `optimization:cpu`, `cost:free`
- **Tasks**: Response caching, semantic similarity, invalidation

## 🏷️ Label System

### Priority Labels
- `priority:high` - Critical for core functionality
- `priority:medium` - Important but not blocking
- `priority:low` - Nice to have features

### Component Labels  
- `core` - Core infrastructure
- `module:voice` - Voice processing
- `module:nlp` - Natural language processing
- `module:vision` - Computer vision
- `module:calendar` - Calendar and scheduling
- `module:web` - Web integration

### Optimization Labels
- `optimization:cpu` - CPU performance improvements
- `optimization:memory` - Memory usage optimization  
- `optimization:quality` - Quality improvements
- `cost:free` - Uses only free technologies

### Status Labels
- `completed` - Fully implemented
- `in-progress` - Currently being worked on
- `blocked` - Waiting for dependencies

## 📊 Current Status Summary

### ✅ Completed (2/13 issues)
- Project setup and structure
- Cache manager

### 🟡 In Progress (3/13 issues)  
- Event bus system (core done)
- Plugin manager (basic done)
- Resource monitor (basic done)

### ⏳ Pending (8/13 issues)
- All voice module issues
- All AI integration issues

## 🎯 Next Steps

1. **Install GitHub CLI** and authenticate
2. **Run the issue creation script**:
   ```bash
   python scripts/create_github_issues.py
   ```
3. **Verify issues created** on GitHub
4. **Start working on** highest priority pending issues

## 📝 Notes

- All issues are designed for **zero-cost** implementation
- Each issue includes detailed **acceptance criteria**
- **Progress tracking** built into issue descriptions
- Issues are **cross-referenced** where dependencies exist

The automated script will create all these issues with proper formatting, labels, and milestone assignments.