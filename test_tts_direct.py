#!/usr/bin/env python3
"""
Direct TTS test to verify pyttsx3 is working
"""

import pyttsx3
import time

def test_tts():
    print("🔊 Testing direct pyttsx3 TTS...")
    
    try:
        # Initialize TTS engine
        engine = pyttsx3.init()
        
        # Get available voices
        voices = engine.getProperty('voices')
        print(f"Available voices: {len(voices) if voices else 0}")
        
        if voices:
            for i, voice in enumerate(voices[:3]):  # Show first 3
                print(f"  {i}: {voice.name if voice.name else 'Unknown'}")
        
        # Test speech
        print("🗣️ Speaking test message...")
        test_message = "It's currently 10 AM"
        
        print(f"TTS: '{test_message}'")
        engine.say(test_message)
        
        print("⏸️ Starting runAndWait...")
        start_time = time.time()
        engine.runAndWait()
        end_time = time.time()
        
        print(f"✅ runAndWait completed in {end_time - start_time:.2f} seconds")
        print("If you heard the message, TTS is working!")
        
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_tts()