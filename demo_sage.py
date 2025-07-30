#!/usr/bin/env python3
"""
SAGE Demo Script - Interactive demonstration of current capabilities
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from main import SAGEApplication


async def demo_sage():
    """Interactive demo of SAGE capabilities"""
    print("🚀 Starting SAGE Demo...")
    print("=" * 60)
    
    # Initialize SAGE
    sage = SAGEApplication()
    await sage.initialize()
    
    # Get all modules
    voice_module = sage.plugin_manager.get_module('voice')
    nlp_module = sage.plugin_manager.get_module('nlp')
    learning_module = sage.plugin_manager.get_module('learning')  
    calendar_module = sage.plugin_manager.get_module('calendar')
    
    # Show module status
    print("\n📊 SAGE Module Status:")
    print("=" * 40)
    print(f"   Voice Module: {'✅ Loaded' if voice_module else '❌ Not available'}")
    print(f"   NLP Module: {'✅ Loaded' if nlp_module else '❌ Not available'}")
    print(f"   Learning Module: {'✅ Loaded' if learning_module else '❌ Not available'}")
    print(f"   Calendar Module: {'✅ Loaded' if calendar_module else '❌ Not available'}")
    
    # Quick NLP Demo
    if nlp_module:
        print("\n🧠 SAGE NLP System Demo")
        print("=" * 40)
        
        try:
            print("   Testing Ollama LLM connection...")
            response = await nlp_module.process_text("Hello, how are you?")
            if response.get('success'):
                print("   ✅ NLP system working")
                print(f"   Response: {response['response']['text'][:60]}...")
            else:
                print(f"   ❌ NLP error: {response.get('error')}")
        except Exception as e:
            print(f"   ❌ NLP test failed: {e}")
    
    # Quick Learning Demo  
    if learning_module:
        print("\n🎓 SAGE Learning System Demo")
        print("=" * 40)
        
        try:
            status = learning_module.get_status()
            stats = status.get('statistics', {})
            cache_sizes = status.get('cache_sizes', {})
            
            print(f"   Total interactions learned: {cache_sizes.get('interactions', 0)}")
            print(f"   User preferences: {cache_sizes.get('preferences', 0)}")
            print(f"   Command patterns: {cache_sizes.get('patterns', 0)}")
            print("   ✅ Learning system operational")
        except Exception as e:
            print(f"   ❌ Learning test failed: {e}")
    
    # Quick Calendar Demo
    if calendar_module:
        print("\n🗓️  SAGE Calendar System Demo")
        print("=" * 40)
        
        try:
            status = calendar_module.get_status()
            stats = status.get('statistics', {})
            
            print(f"   Total events: {stats.get('total_events', 0)}")
            print(f"   Upcoming events: {stats.get('upcoming_events', 0)}")
            print(f"   Pending reminders: {stats.get('pending_reminders', 0)}")
            print("   ✅ Calendar system operational")
        except Exception as e:
            print(f"   ❌ Calendar test failed: {e}")
    
    # Voice Demo (if available)
    if voice_module:
        print("\n🎙️ SAGE Voice System Demo")
        print("=" * 40)
    
    try:
        # Demo 1: Basic Text-to-Speech
        print("\n1️⃣ Basic Text-to-Speech:")
        print("   Attempting to speak: 'Hello! I am SAGE, your AI assistant.'")
        try:
            result = await voice_module.speak_text("Hello! I am SAGE, your AI assistant.")
            print(f"   Result: {'✅ Success' if result else '❌ Failed (missing eSpeak)'}")
        except Exception as e:
            print(f"   Result: ❌ Error: {e}")
        
        # Demo 2: Emotional Speech
        print("\n2️⃣ Emotional Speech:")
        emotions = ['excited', 'happy', 'cheerful']
        for emotion in emotions:
            print(f"   Speaking with {emotion} emotion...")
            try:
                result = await voice_module.speak_with_emotion(
                    f"I am feeling {emotion} today!", emotion, intensity=1.0
                )
                print(f"   {emotion.capitalize()}: {'✅' if result else '❌'}")
            except Exception as e:
                print(f"   {emotion.capitalize()}: ❌ Error: {e}")
        
        # Demo 3: Voice Profiles
        print("\n3️⃣ Voice Profiles:")
        profiles = ['notification', 'alert']
        for profile in profiles:
            print(f"   Testing {profile} profile...")
            try:
                if profile == 'notification':
                    result = await voice_module.speak_notification("You have a new message")
                else:
                    result = await voice_module.speak_alert("This is an important alert!")
                print(f"   {profile.capitalize()}: {'✅' if result else '❌'}")
            except Exception as e:
                print(f"   {profile.capitalize()}: ❌ Error: {e}")
        
        # Demo 4: Available Voices
        print("\n4️⃣ Available Voices:")
        try:
            voices = await voice_module.get_available_voices()
            if voices:
                print(f"   Found {len(voices)} available voices:")
                for i, voice in enumerate(voices[:3]):  # Show first 3
                    print(f"   {i+1}. {voice.get('name', 'Unknown')} ({voice.get('engine', 'Unknown')})")
                if len(voices) > 3:
                    print(f"   ... and {len(voices) - 3} more")
            else:
                print("   ❌ No voices available")
        except Exception as e:
            print(f"   ❌ Error getting voices: {e}")
        
        # Demo 5: Voice Recognition (if available)
        print("\n5️⃣ Voice Recognition:")
        try:
            # This will fail without microphone but shows the capability
            print("   Voice recognition system status:")
            if hasattr(voice_module, 'recognition_engine') and voice_module.recognition_engine:
                rec_status = voice_module.recognition_engine.get_status()
                deps = rec_status.get('dependencies', {})
                print(f"   Whisper: {'✅' if deps.get('whisper') else '❌'}")
                print(f"   PyAudio: {'✅' if deps.get('pyaudio') else '❌ (needed for microphone)'}")
                print(f"   Speech Recognition: {'✅' if deps.get('speech_recognition') else '❌'}")
            else:
                print("   ❌ Recognition engine not available")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Demo 6: Audio Processing
        print("\n6️⃣ Audio Processing:")
        try:
            if hasattr(voice_module, 'audio_processor') and voice_module.audio_processor:
                proc_status = voice_module.audio_processor.get_status()
                print("   Audio processing capabilities:")
                print(f"   VAD (Voice Activity Detection): {'✅' if proc_status.get('vad_available') else '❌'}")
                print(f"   Noise Reduction: {'✅' if proc_status.get('noise_reduction_enabled') else '❌'}")
                print(f"   Auto Gain Control: {'✅' if proc_status.get('auto_gain_control') else '❌'}")
                print(f"   Compression: {'✅' if proc_status.get('compressor_enabled') else '❌'}")
                
                # Show dependency status
                deps = proc_status.get('dependencies', {})
                print("   Dependencies:")
                print(f"   SciPy: {'✅' if deps.get('scipy') else '❌'}")
                print(f"   Librosa: {'✅' if deps.get('librosa') else '❌'}")
                print(f"   SoundFile: {'✅' if deps.get('soundfile') else '❌'}")
            else:
                print("   ❌ Audio processor not available")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Demo 7: System Status
        print("\n7️⃣ System Status:")
        try:
            voice_status = voice_module.get_voice_status()
            print("   Overall system health:")
            print(f"   Voice Module: {'✅ Loaded' if voice_status.get('loaded') else '❌ Not loaded'}")
            print(f"   Recognition: {'✅ Available' if voice_status.get('recognition_available') else '❌ Unavailable'}")
            print(f"   Synthesis: {'✅ Available' if voice_status.get('synthesis_available') else '❌ Unavailable'}")
            print(f"   Wake Word: {'✅ Available' if voice_status.get('wake_word_available') else '❌ Unavailable'}")
            print(f"   Audio Processing: {'✅ Available' if voice_status.get('audio_processor_available') else '❌ Unavailable'}")
        except Exception as e:
            print(f"   ❌ Error getting status: {e}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    print("\n🎯 NEXT STEPS:")
    print("=" * 40)
    print("To unlock full voice capabilities, install:")
    print("   pip install pyaudio speech-recognition")
    print("   sudo apt install espeak espeak-data")
    print("")
    print("Then you can:")
    print("   • Use microphone for voice recognition")
    print("   • Hear actual speech output")
    print("   • Test wake word detection")
    print("   • Process real-time audio streams")
    
    # Shutdown
    await sage.shutdown()
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_sage())