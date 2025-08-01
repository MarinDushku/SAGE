#!/usr/bin/env python3
"""
Simple voice recognition test to verify speech processing
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.voice.enhanced_recognition import EnhancedVoiceRecognition


async def test_voice_recognition():
    """Test voice recognition directly"""
    print("🎤 Testing Voice Recognition")
    print("=" * 40)
    
    # Configuration
    config = {
        'engine': 'whisper',
        'model': 'tiny',
        'language': 'en',
        'energy_threshold': 300,  # Higher threshold
        'debug_mode': True,
        'audio_monitoring': True
    }
    
    # Initialize recognition
    recognition = EnhancedVoiceRecognition(config)
    
    # Test initialization
    print("Initializing...")
    if not await recognition.initialize():
        print("❌ Initialization failed")
        return
    
    print("✅ Initialization successful")
    
    # Start listening
    print("Starting voice recognition...")
    if not await recognition.start_listening():
        print("❌ Could not start listening")
        return
    
    print("✅ Listening started")
    print("\n🗣️  Say something clearly now...")
    print("   (Will listen for 10 seconds)")
    
    # Listen for 10 seconds
    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < 10:
        # Check for recognized text
        result = await recognition.get_recognized_text()
        if result:
            text = result['text']
            confidence = result['confidence']
            print(f"✅ Heard: '{text}' (confidence: {confidence:.2f})")
            
            # Test wake word detection
            if any(wake in text.lower() for wake in ['sage', 'computer']):
                print("🎯 Wake word detected!")
            else:
                print("⚠️  No wake word in recognized text")
        
        await asyncio.sleep(0.1)
    
    print("\n⏰ Test complete")
    
    # Stop and shutdown
    await recognition.stop_listening()
    await recognition.shutdown()
    
    # Show stats
    status = recognition.get_status()
    stats = status.get('statistics', {})
    print(f"\n📊 Recognition Stats:")
    print(f"   Attempts: {stats.get('recognitions_attempted', 0)}")
    print(f"   Successful: {stats.get('recognitions_successful', 0)}")
    print(f"   Failed: {stats.get('recognitions_failed', 0)}")


if __name__ == "__main__":
    asyncio.run(test_voice_recognition())