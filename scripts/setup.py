#!/usr/bin/env python3
"""
Complete setup script for SAGE - Zero Cost Edition
Smart Adaptive General Executive Setup
"""

import os
import subprocess
import sys
import platform
import urllib.request
from pathlib import Path
import json
import shutil


class SAGESetup:
    """Setup manager for SAGE installation"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = platform.machine().lower()
        self.sage_root = Path(__file__).parent.parent
        self.venv_path = self.sage_root / "venv"
        self.minimal = False
        self.skip_ollama = False
        self.skip_models = False
        
    def print_banner(self):
        """Print SAGE setup banner"""
        print("=" * 60)
        print("🚀 SAGE - Smart Adaptive General Executive")
        print("   Zero-Cost AI Desktop Assistant Setup")
        print("=" * 60)
        print(f"System: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print(f"Architecture: {self.architecture}")
        print("=" * 60)
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        if sys.version_info < (3, 8):
            print("❌ Error: Python 3.8 or higher is required")
            print(f"Current version: {sys.version}")
            return False
        print("✅ Python version compatible")
        return True
        
    def create_virtual_environment(self):
        """Create Python virtual environment"""
        print("📦 Creating virtual environment...")
        
        if self.venv_path.exists():
            print("Virtual environment already exists. Removing...")
            shutil.rmtree(self.venv_path)
            
        try:
            subprocess.run([
                sys.executable, "-m", "venv", str(self.venv_path)
            ], check=True)
            print("✅ Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
            
    def get_pip_path(self):
        """Get pip executable path for the virtual environment"""
        if self.system == "windows":
            return self.venv_path / "Scripts" / "pip.exe"
        else:
            return self.venv_path / "bin" / "pip"
            
    def get_python_path(self):
        """Get Python executable path for the virtual environment"""
        if self.system == "windows":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
            
    def install_system_dependencies(self):
        """Install system-level dependencies"""
        print("🔧 Installing system dependencies...")
        
        if self.system == "linux":
            # Ubuntu/Debian dependencies
            print("Installing basic system dependencies...")
            try:
                # Update package list first
                subprocess.run(["sudo", "apt", "update"], check=True)
                
                # Install essential dependencies
                essential_deps = [
                    "python3-dev", "python3-pip", "build-essential"
                ]
                subprocess.run(["sudo", "apt", "install", "-y"] + essential_deps, check=True)
                print("✅ Essential system dependencies installed")
                
                # Try to install optional audio/vision dependencies
                optional_deps = [
                    "portaudio19-dev", "espeak-ng", "tesseract-ocr", "ffmpeg"
                ]
                try:
                    subprocess.run(["sudo", "apt", "install", "-y"] + optional_deps, check=True)
                    print("✅ Optional dependencies installed")
                except subprocess.CalledProcessError:
                    print("⚠️  Some optional dependencies may not have installed")
                    print("For voice features, install manually:")
                    print("  sudo apt install portaudio19-dev espeak-ng tesseract-ocr ffmpeg")
                    
            except subprocess.CalledProcessError as e:
                print("⚠️  System dependency installation had issues")
                print("Please install manually if needed:")
                print("  sudo apt update")
                print("  sudo apt install python3-dev build-essential")
                
        elif self.system == "darwin":  # macOS
            print("Please install Homebrew dependencies manually:")
            print("  brew install portaudio espeak tesseract ffmpeg")
            
        elif self.system == "windows":
            print("Windows system dependencies:")
            print("  - Microsoft Visual C++ Build Tools")
            print("  - Tesseract OCR (https://github.com/UB-Mannheim/tesseract/wiki)")
            
    def install_python_dependencies(self, minimal=False):
        """Install Python dependencies"""
        if minimal:
            print("📚 Installing minimal Python dependencies...")
            requirements_file = self.sage_root / "requirements-minimal.txt"
        else:
            print("📚 Installing full Python dependencies...")
            requirements_file = self.sage_root / "requirements.txt"
        
        pip_path = self.get_pip_path()
        
        if not requirements_file.exists():
            print(f"❌ Requirements file not found: {requirements_file}")
            return False
            
        try:
            # Upgrade pip first
            subprocess.run([
                str(pip_path), "install", "--upgrade", "pip"
            ], check=True)
            
            # Install requirements
            subprocess.run([
                str(pip_path), "install", "-r", str(requirements_file)
            ], check=True)
            
            print("✅ Python dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Python dependencies: {e}")
            if not minimal:
                print("\n🔄 Trying minimal installation...")
                return self.install_python_dependencies(minimal=True)
            else:
                print("Try installing manually with:")
                print(f"  {pip_path} install -r {requirements_file}")
                return False
            
    def install_ollama(self):
        """Install Ollama for local LLM"""
        print("🤖 Installing Ollama...")
        
        if shutil.which("ollama"):
            print("✅ Ollama already installed")
            return True
            
        try:
            if self.system == "linux" or self.system == "darwin":
                # Download and run install script
                install_script = "curl -fsSL https://ollama.ai/install.sh | sh"
                subprocess.run(install_script, shell=True, check=True)
                
            elif self.system == "windows":
                print("Please install Ollama manually from: https://ollama.ai/download")
                input("Press Enter after installing Ollama...")
                
            print("✅ Ollama installation completed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Ollama: {e}")
            print("Please install manually from: https://ollama.ai/download")
            return False
            
    def download_ai_models(self):
        """Download free AI models"""
        print("📥 Downloading AI models...")
        
        models_to_download = [
            ("phi3:mini", "Phi3 Mini - 3.8GB"),
            ("llama3.2:1b", "Llama 3.2 1B - 1.3GB"),  
        ]
        
        for model, description in models_to_download:
            print(f"Downloading {description}...")
            try:
                subprocess.run([
                    "ollama", "pull", model
                ], check=True)
                print(f"✅ Downloaded {model}")
            except subprocess.CalledProcessError:
                print(f"⚠️  Failed to download {model}")
                
    def download_whisper_models(self):
        """Download Whisper models"""
        print("🎤 Downloading Whisper models...")
        
        python_path = self.get_python_path()
        
        try:
            # Download tiny model for speed
            subprocess.run([
                str(python_path), "-c", 
                "import whisper; whisper.load_model('tiny')"
            ], check=True)
            
            # Download base model for better accuracy
            subprocess.run([
                str(python_path), "-c",
                "import whisper; whisper.load_model('base')"
            ], check=True)
            
            print("✅ Whisper models downloaded")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to download Whisper models: {e}")
            return False
            
    def create_config_files(self):
        """Create initial configuration files"""
        print("⚙️  Creating configuration files...")
        
        # Main config
        config_file = self.sage_root / "config.yaml"
        if not config_file.exists():
            config_content = """# SAGE Configuration
core:
  log_level: INFO
  max_workers: 4
  event_queue_size: 1000
  resource_monitor_interval: 30

performance:
  max_memory_mb: 1000
  max_cpu_percent: 80
  cache_size_mb: 200
  model_loading_timeout: 60

modules:
  auto_load:
    - voice
    - nlp
    - calendar
  optional:
    - vision
    - web_tools
    - fabrication

voice:
  recognition:
    engine: whisper  # whisper, google, vosk
    model: tiny
    language: en
  synthesis:
    engine: pyttsx3
    rate: 200
    volume: 0.8
  wake_word:
    enabled: true
    keyword: sage
    sensitivity: 0.5

nlp:
  llm:
    provider: ollama
    model: phi3:mini
    temperature: 0.7
    max_tokens: 1000
    
vision:
  enabled: false  # Enable manually if needed
  
web_tools:
  enabled: true
  
fabrication:
  enabled: false  # Enable manually if needed
"""
            with open(config_file, 'w') as f:
                f.write(config_content)
            print("✅ Configuration file created")
            
        # .env file
        env_file = self.sage_root / ".env"
        if not env_file.exists():
            env_content = """# SAGE Environment Variables
SAGE_LOG_LEVEL=INFO
SAGE_CACHE_DIR=data/cache
SAGE_DATA_DIR=data
SAGE_MODELS_DIR=data/models

# Optional API keys (all free tiers)
# OPENWEATHER_API_KEY=your_key_here
# NEWS_API_KEY=your_key_here
"""
            with open(env_file, 'w') as f:
                f.write(env_content)
            print("✅ Environment file created")
            
    def create_startup_scripts(self):
        """Create startup scripts"""
        print("🚀 Creating startup scripts...")
        
        if self.system == "windows":
            # Windows batch file
            startup_script = self.sage_root / "start_sage.bat"
            script_content = f"""@echo off
cd /d "{self.sage_root}"
"{self.get_python_path()}" main.py
pause
"""
            with open(startup_script, 'w') as f:
                f.write(script_content)
                
        else:
            # Unix shell script
            startup_script = self.sage_root / "start_sage.sh"
            script_content = f"""#!/bin/bash
cd "{self.sage_root}"
"{self.get_python_path()}" main.py
"""
            with open(startup_script, 'w') as f:
                f.write(script_content)
            startup_script.chmod(0o755)
            
        print("✅ Startup scripts created")
        
    def verify_installation(self):
        """Verify that installation was successful"""
        print("🔍 Verifying installation...")
        
        python_path = self.get_python_path()
        
        # Test imports
        test_imports = [
            "import asyncio",
            "import yaml",
            "import psutil", 
            "import speech_recognition",
            "import pyttsx3",
            "import whisper",
            "import cv2",
            "import spacy"
        ]
        
        failed_imports = []
        
        for import_test in test_imports:
            try:
                subprocess.run([
                    str(python_path), "-c", import_test
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                failed_imports.append(import_test.split()[-1])
                
        if failed_imports:
            print(f"⚠️  Some modules failed to import: {failed_imports}")
            print("Installation completed with warnings")
        else:
            print("✅ All core modules imported successfully")
            
        # Check Ollama
        if shutil.which("ollama"):
            try:
                result = subprocess.run(
                    ["ollama", "list"], 
                    capture_output=True, 
                    text=True
                )
                if "phi3" in result.stdout or "llama" in result.stdout:
                    print("✅ Ollama models available")
                else:
                    print("⚠️  No Ollama models found")
            except:
                print("⚠️  Ollama installation check failed")
        else:
            print("⚠️  Ollama not found in PATH")
            
    def run_setup(self):
        """Run the complete setup process"""
        self.print_banner()
        
        if not self.check_python_version():
            return False
            
        print("\n🔧 Starting SAGE setup process...\n")
        
        # Core setup
        if not self.create_virtual_environment():
            return False
            
        if not self.minimal:
            self.install_system_dependencies()
        else:
            print("🔧 Skipping system dependencies (minimal install)")
        
        if not self.install_python_dependencies(minimal=self.minimal):
            return False
            
        # AI models setup (skip if requested)
        if not self.skip_ollama and not self.minimal:
            if not self.install_ollama():
                print("⚠️  Continuing without Ollama")
        else:
            print("🤖 Skipping Ollama installation")
            
        if not self.skip_models and not self.minimal:
            self.download_ai_models()
            self.download_whisper_models()
        else:
            print("📥 Skipping AI model downloads")
        
        # Configuration
        self.create_config_files()
        self.create_startup_scripts()
        
        # Verification
        self.verify_installation()
        
        print("\n" + "=" * 60)
        print("🎉 SAGE setup completed!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Activate virtual environment:")
        if self.system == "windows":
            print(f"   {self.venv_path}\\Scripts\\activate")
        else:
            print(f"   source {self.venv_path}/bin/activate")
        print("2. Run SAGE:")
        print("   python main.py")
        print("3. Or use startup script:")
        if self.system == "windows":
            print("   start_sage.bat")
        else:
            print("   ./start_sage.sh")
        print("\n📖 Check README.md for detailed usage instructions")
        print("🐛 Report issues at: https://github.com/your-repo/SAGE/issues")
        
        return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SAGE Setup Script")
    parser.add_argument("--minimal", action="store_true", 
                       help="Install only minimal dependencies for core functionality")
    parser.add_argument("--skip-ollama", action="store_true",
                       help="Skip Ollama installation")
    parser.add_argument("--skip-models", action="store_true", 
                       help="Skip AI model downloads")
    
    args = parser.parse_args()
    
    setup = SAGESetup()
    setup.minimal = args.minimal
    setup.skip_ollama = args.skip_ollama  
    setup.skip_models = args.skip_models
    
    success = setup.run_setup()
    sys.exit(0 if success else 1)