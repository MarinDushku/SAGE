#!/usr/bin/env python3
"""
Voice Recognition Diagnostic Tool - Test microphone and voice pipeline
"""

import sys
import asyncio
import time
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from modules.voice.enhanced_recognition import EnhancedVoiceRecognition
import speech_recognition as sr


class VoiceDiagnostic:
    """Diagnostic tool to test voice recognition components"""
    
    def __init__(self):
        self.recognition = None
        self.microphone = None
        self.recognizer = None
        
    async def run_full_diagnostic(self):
        """Run complete voice recognition diagnostic"""
        print("🔧 SAGE Voice Recognition Diagnostic Tool")
        print("=" * 60)
        print("This tool will help determine if the issue is:")
        print("• Microphone hardware access")
        print("• Audio level detection") 
        print("• Speech recognition processing")
        print("• Wake word detection")
        print()
        
        # Test 1: Basic microphone access
        print("Test 1: Microphone Hardware Access")
        print("-" * 40)
        mic_working = await self.test_microphone_access()
        
        if not mic_working:
            print("❌ MICROPHONE ISSUE: Cannot access microphone")
            print("This is likely the root cause of the problem.")
            print()
            print("Possible solutions:")
            print("• Check if microphone is connected and working")
            print("• On Windows: Check microphone permissions")
            print("• On WSL: Voice hardware access may be limited")
            print("• Try running on native Windows instead of WSL")
            return False
        
        # Test 2: Audio level monitoring
        print("\nTest 2: Audio Level Detection")
        print("-" * 40)
        await self.test_audio_levels()
        
        # Test 3: Speech recognition
        print("\nTest 3: Speech Recognition Engine")
        print("-" * 40)
        recognition_working = await self.test_speech_recognition()
        
        # Test 4: Enhanced recognition system
        print("\nTest 4: Enhanced Recognition System") 
        print("-" * 40)
        enhanced_working = await self.test_enhanced_recognition()
        
        # Test 5: Wake word detection
        print("\nTest 5: Wake Word Detection")
        print("-" * 40)
        await self.test_wake_word_detection()
        
        # Final diagnosis
        print("\n🎯 DIAGNOSTIC RESULTS")
        print("=" * 60)
        
        if mic_working and recognition_working and enhanced_working:
            print("✅ All systems operational - voice recognition should work")
            print()
            print("If SAGE still isn't responding, the issue may be:")
            print("• Audio threshold too high (try speaking louder)")
            print("• Background noise interfering")
            print("• Wake word not being detected clearly")
            print("• Need to speak directly into microphone")
        elif mic_working and recognition_working:
            print("⚠️  Basic systems work, enhanced system has issues")
            print("The original SAGE voice module might work better")
        elif mic_working:
            print("⚠️  Microphone works but speech recognition has issues")
            print("Try installing/updating speech recognition dependencies")
        else:
            print("❌ Multiple system failures detected")
        
        return mic_working and recognition_working
    
    async def test_microphone_access(self) -> bool:
        """Test basic microphone access"""
        try:
            print("Testing microphone access...")
            
            # Initialize speech recognition
            self.recognizer = sr.Recognizer()
            
            # Try to list microphones
            mic_list = sr.Microphone.list_microphone_names()
            print(f"Available microphones: {len(mic_list)}")
            for i, name in enumerate(mic_list[:3]):  # Show first 3
                print(f"  {i}: {name}")
            
            if not mic_list:
                print("❌ No microphones detected")
                return False
            
            # Try to access default microphone
            self.microphone = sr.Microphone()
            
            print("✅ Microphone access successful")
            return True
            
        except Exception as e:
            print(f"❌ Microphone access failed: {e}")
            return False
    
    async def test_audio_levels(self):
        """Test audio level detection"""
        try:
            print("Testing audio level detection...")
            print("Please speak now for 3 seconds...")
            
            with self.microphone as source:
                print("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print(f"Energy threshold: {self.recognizer.energy_threshold}")
                
                print("Listening for audio...")
                start_time = time.time()
                audio_detected = False
                
                while time.time() - start_time < 3:
                    try:
                        # Try to detect audio with short timeout
                        audio = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=1)
                        if audio:
                            audio_detected = True
                            print("✅ Audio detected!")
                            break
                    except sr.WaitTimeoutError:
                        print(".", end="", flush=True)
                        continue
                
                print()
                
                if audio_detected:
                    print("✅ Audio level detection working")
                else:
                    print("❌ No audio detected - try speaking louder or closer to microphone")
                    
        except Exception as e:
            print(f"❌ Audio level test failed: {e}")
    
    async def test_speech_recognition(self) -> bool:
        """Test speech recognition engine"""
        try:
            print("Testing speech recognition...")
            print("Say something for 3 seconds...")
            
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                try:
                    # Listen for speech
                    print("Listening...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                    print("Processing speech...")
                    
                    # Try Google Speech Recognition first
                    try:
                        text = self.recognizer.recognize_google(audio)
                        print(f"✅ Google SR recognized: '{text}'")
                        return True
                    except sr.UnknownValueError:
                        print("❌ Google SR: Could not understand audio")
                    except sr.RequestError as e:
                        print(f"❌ Google SR: {e}")
                    
                    # Try Whisper if available
                    try:
                        text = self.recognizer.recognize_whisper(audio)
                        print(f"✅ Whisper recognized: '{text}'")
                        return True
                    except sr.UnknownValueError:
                        print("❌ Whisper: Could not understand audio")
                    except Exception as e:
                        print(f"❌ Whisper: {e}")
                    
                    return False
                    
                except sr.WaitTimeoutError:
                    print("❌ No speech detected in time limit")
                    return False
                    
        except Exception as e:
            print(f"❌ Speech recognition test failed: {e}")
            return False
    
    async def test_enhanced_recognition(self) -> bool:
        """Test SAGE's enhanced recognition system"""
        try:
            print("Testing SAGE enhanced recognition system...")
            
            # Initialize enhanced recognition
            config = {
                'engine': 'whisper',
                'model': 'tiny',
                'language': 'en',
                'energy_threshold': 300,
                'debug_mode': True,
                'audio_monitoring': True
            }
            
            self.recognition = EnhancedVoiceRecognition(config)
            
            # Test initialization
            if not await self.recognition.initialize():
                print("❌ Enhanced recognition initialization failed")
                return False
            
            print("✅ Enhanced recognition initialized")
            
            # Get status
            status = self.recognition.get_status()
            print(f"Microphone working: {status['microphone_working']}")
            print(f"Calibration successful: {status['calibration_successful']}")
            print(f"Engine: {status['engine']}")
            print(f"Model: {status['model']}")
            
            # Test if we can start listening
            print("Testing listening capability...")
            can_listen = await self.recognition.start_listening()
            
            if can_listen:
                print("✅ Enhanced recognition can start listening")
                await asyncio.sleep(1)  # Brief test
                await self.recognition.stop_listening()
                return True
            else:
                print("❌ Enhanced recognition cannot start listening")
                return False
                
        except Exception as e:
            print(f"❌ Enhanced recognition test failed: {e}")
            return False
        finally:
            if self.recognition:
                await self.recognition.shutdown()
    
    async def test_wake_word_detection(self):
        """Test wake word detection logic"""
        try:
            print("Testing wake word detection logic...")
            
            test_phrases = [
                "hey sage schedule a meeting",
                "sage what time is it",
                "computer show my calendar", 
                "hello there sage",
                "schedule meeting tomorrow",  # No wake word
                "what do I have today"       # No wake word
            ]
            
            wake_words = ['sage', 'hey sage', 'computer', 'hey computer']
            
            for phrase in test_phrases:
                detected = False
                detected_word = None
                
                for wake_word in wake_words:
                    if wake_word in phrase.lower():
                        detected = True
                        detected_word = wake_word
                        break
                
                status = "✅" if detected else "❌"
                word_info = f" ('{detected_word}')" if detected_word else ""
                print(f"  {status} '{phrase}'{word_info}")
            
            print("✅ Wake word detection logic working")
            
        except Exception as e:
            print(f"❌ Wake word test failed: {e}")
    
    async def interactive_voice_test(self):
        """Interactive voice test with real-time feedback"""
        print("\n🎤 Interactive Voice Test")
        print("=" * 60)
        print("This will test the complete voice pipeline with real-time feedback.")
        print("Say 'Hey Sage, what time is it' or similar commands.")
        print("Press Ctrl+C to stop.")
        print()
        
        try:
            # Set up real-time audio monitoring
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            
            print("Adjusting for ambient noise...")
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
            
            print(f"Energy threshold: {recognizer.energy_threshold}")
            print("Listening... (speak now)")
            
            while True:
                try:
                    with microphone as source:
                        # Listen with short timeout for responsiveness
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    
                    print("🔄 Processing audio...")
                    
                    # Try recognition
                    try:
                        text = recognizer.recognize_google(audio)
                        print(f"🗣️  Heard: '{text}'")
                        
                        # Test wake word detection
                        if any(wake in text.lower() for wake in ['sage', 'computer']):
                            print("✅ Wake word detected!")
                            command = text.lower()
                            for wake in ['hey sage', 'sage', 'hey computer', 'computer']:
                                command = command.replace(wake, '').strip()
                            print(f"📝 Command: '{command}'")
                        else:
                            print("❌ No wake word detected")
                        
                        print("-" * 40)
                        
                    except sr.UnknownValueError:
                        print("❓ Could not understand audio")
                    except sr.RequestError as e:
                        print(f"❌ Recognition error: {e}")
                
                except sr.WaitTimeoutError:
                    print(".", end="", flush=True)
                    continue
                except KeyboardInterrupt:
                    print("\nStopping interactive test...")
                    break
                
        except Exception as e:
            print(f"❌ Interactive test failed: {e}")


async def main():
    """Main diagnostic function"""
    diagnostic = VoiceDiagnostic()
    
    try:
        # Run full diagnostic
        await diagnostic.run_full_diagnostic()
        
        # Ask if user wants interactive test
        print("\n" + "=" * 60)
        response = input("Run interactive voice test? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            await diagnostic.interactive_voice_test()
        
        print("\n🎉 Diagnostic complete!")
        print("If microphone and recognition are working but SAGE still doesn't respond:")
        print("• Try speaking louder and clearer")
        print("• Ensure you're saying 'Hey Sage' or 'Sage' clearly")
        print("• Check if there's background noise interference")
        print("• Try running SAGE with fallback text input mode")
        
    except KeyboardInterrupt:
        print("\nDiagnostic interrupted by user")
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())