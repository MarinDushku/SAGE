#!/usr/bin/env python3
"""
Test script to verify Issue #1: Project setup and structure
"""

import os
import sys
from pathlib import Path
import importlib.util

def test_folder_structure():
    """Test if folder structure matches specification"""
    print("🧪 Testing folder structure...")
    
    required_dirs = [
        "core",
        "modules/voice", 
        "modules/nlp",
        "modules/vision",
        "modules/calendar", 
        "modules/web_tools",
        "modules/integrations",
        "modules/learning",
        "modules/fabrication",
        "modules/custom_skills/skills",
        "ui/module_widgets",
        "ui/assets/icons",
        "ui/assets/sounds", 
        "data/models/whisper",
        "data/models/yolo",
        "data/models/llm",
        "data/user_data/face_encodings",
        "data/cache/voice",
        "data/cache/llm", 
        "data/cache/web",
        "data/logs",
        "tests/unit",
        "tests/integration",
        "tests/performance",
        "tests/fixtures",
        "scripts",
        "docs",
        ".github/workflows",
        ".github/ISSUE_TEMPLATE"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
            
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    else:
        print("✅ All required directories exist")
        return True

def test_core_files():
    """Test if core files exist and are importable"""
    print("\n🧪 Testing core files...")
    
    required_files = {
        "main.py": "Main entry point",
        "config.yaml": "Main configuration", 
        "requirements.txt": "Python requirements",
        "requirements-dev.txt": "Development requirements",
        "README.md": "Project documentation",
        "LICENSE": "License file",
        ".gitignore": "Git ignore file",
        ".env.example": "Environment example",
        "scripts/setup.py": "Setup script"
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if not Path(file_path).exists():
            missing_files.append(f"{file_path} ({description})")
            
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_core_modules():
    """Test if core modules can be imported"""
    print("\n🧪 Testing core module imports...")
    
    core_modules = [
        "core.event_bus",
        "core.plugin_manager", 
        "core.config_manager",
        "core.resource_monitor",
        "core.cache_manager",
        "core.logger"
    ]
    
    failed_imports = []
    for module_name in core_modules:
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                failed_imports.append(module_name)
            else:
                # Try to actually import it
                importlib.import_module(module_name)
        except Exception as e:
            failed_imports.append(f"{module_name} ({e})")
            
    if failed_imports:
        print(f"❌ Failed imports: {failed_imports}")
        return False
    else:
        print("✅ All core modules can be imported")
        return True

def test_requirements():
    """Test if requirements.txt contains only free technologies"""
    print("\n🧪 Testing requirements for free technologies...")
    
    try:
        with open("requirements.txt", "r") as f:
            requirements = f.read()
            
        # Check for any paid/commercial services
        paid_indicators = [
            "openai==",  # OpenAI API (paid)
            "anthropic==", # Anthropic API (paid)
            "cohere==",  # Cohere API (paid)
        ]
        
        found_paid = []
        for indicator in paid_indicators:
            if indicator in requirements:
                found_paid.append(indicator)
                
        if found_paid:
            print(f"⚠️  Found potential paid services: {found_paid}")
            return False
        else:
            print("✅ Requirements contain only free technologies")
            return True
            
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False

def test_git_setup():
    """Test if git repository is properly configured"""
    print("\n🧪 Testing git configuration...")
    
    try:
        # Check if .git directory exists
        if not Path(".git").exists():
            print("❌ Not a git repository")
            return False
            
        # Check if remote is set correctly
        import subprocess
        result = subprocess.run(
            ["git", "remote", "-v"], 
            capture_output=True, 
            text=True
        )
        
        if "MarinDushku/SAGE" not in result.stdout:
            print(f"❌ Git remote not set to MarinDushku/SAGE")
            print(f"Current remotes: {result.stdout}")
            return False
            
        print("✅ Git repository properly configured")
        return True
        
    except Exception as e:
        print(f"❌ Error checking git setup: {e}")
        return False

def test_main_entry_point():
    """Test if main.py can be executed"""
    print("\n🧪 Testing main entry point...")
    
    try:
        # Test if main.py has the right structure
        with open("main.py", "r") as f:
            content = f.read()
            
        required_elements = [
            "SAGEApplication",
            "async def main()",
            "if __name__ == \"__main__\":",
            "asyncio.run(main())"
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
                
        if missing_elements:
            print(f"❌ Missing elements in main.py: {missing_elements}")
            return False
        else:
            print("✅ Main entry point has correct structure")
            return True
            
    except Exception as e:
        print(f"❌ Error testing main.py: {e}")
        return False

def main():
    """Run all tests for Issue #1"""
    print("🧪 Testing Issue #1: Project setup and structure")
    print("=" * 60)
    
    tests = [
        test_folder_structure,
        test_core_files,
        test_core_modules,
        test_requirements,
        test_git_setup,
        test_main_entry_point
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
            
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Issue #1 is COMPLETE! All acceptance criteria met.")
        return True
    else:
        print("⚠️  Issue #1 needs attention. Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)