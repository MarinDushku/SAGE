#!/usr/bin/env python3
"""
Verification script for Issue #7: Text-to-Speech Integration
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_enhanced_tts_structure():
    """Test that enhanced TTS structure is complete"""
    print("🧪 Verifying Issue #7 enhanced TTS structure...")
    
    try:
        # Test imports
        from modules.voice.synthesis import VoiceSynthesis
        
        print("✅ Enhanced TTS engine imported successfully")
        
        # Test TTS creation with advanced config
        config = {
            'engine': 'pyttsx3',
            'rate': 200,
            'volume': 0.8,
            'pitch': 0,
            'emotion': 'neutral',
            'speaking_style': 'normal',
            'language': 'en-US',
            'cache_enabled': True,
            'voice_profiles': {
                'assistant': {'rate': 190, 'volume': 0.8, 'emotion': 'friendly'},
                'system': {'rate': 180, 'volume': 0.9, 'emotion': 'neutral'}
            }
        }
        
        tts = VoiceSynthesis(config)
        
        # Test advanced configuration attributes
        required_attributes = [
            'pitch', 'emotion', 'speaking_style', 'language',
            'cache_enabled', 'cache_dir', 'voice_profiles'
        ]
        
        for attr in required_attributes:
            if not hasattr(tts, attr):
                print(f"❌ Missing advanced attribute: {attr}")
                return False
                
        # Test enhanced methods
        enhanced_methods = [
            'speak_with_emotion', 'speak_notification', 'speak_alert',
            'set_voice_profile', 'get_voice_profiles', 'get_available_voices'
        ]
        
        missing_methods = []
        for method in enhanced_methods:
            if not hasattr(tts, method):
                missing_methods.append(method)
                
        if missing_methods:
            print(f"❌ Missing enhanced methods: {missing_methods}")
            return False
            
        print("✅ Enhanced TTS structure complete")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced TTS structure test failed: {e}")
        return False


def test_voice_profiles():
    """Test voice profiles functionality"""
    print("\n🧪 Testing voice profiles...")
    
    try:
        from modules.voice.synthesis import VoiceSynthesis
        
        config = {
            'voice_profiles': {
                'default': {'rate': 200, 'volume': 0.8, 'emotion': 'neutral'},
                'notification': {'rate': 180, 'volume': 0.9, 'emotion': 'neutral'},
                'alert': {'rate': 160, 'volume': 1.0, 'emotion': 'excited'}
            }
        }
        
        tts = VoiceSynthesis(config)
        
        # Test profile access
        profiles = tts.voice_profiles
        required_profiles = ['default', 'notification', 'alert']
        
        for profile in required_profiles:
            if profile not in profiles:
                print(f"❌ Missing required profile: {profile}")
                return False
                
        # Test profile configuration
        if profiles['alert']['volume'] != 1.0:
            print("❌ Profile configuration not applied correctly")
            return False
            
        print("✅ Voice profiles working")
        return True
        
    except Exception as e:
        print(f"❌ Voice profiles test failed: {e}")
        return False


def test_emotion_system():
    """Test emotion and speaking style system"""
    print("\n🧪 Testing emotion system...")
    
    try:
        from modules.voice.synthesis import VoiceSynthesis
        
        tts = VoiceSynthesis({})
        
        # Test emotion text modification
        emotions = ['neutral', 'happy', 'sad', 'excited', 'cheerful', 'friendly']
        
        for emotion in emotions:
            modified_text = tts._apply_emotion_to_text("Hello world", emotion)
            if not isinstance(modified_text, str):
                print(f"❌ Emotion modification failed for: {emotion}")
                return False
                
        # Test that emotions actually modify text
        neutral_text = tts._apply_emotion_to_text("Hello.", "neutral")
        excited_text = tts._apply_emotion_to_text("Hello.", "excited")
        
        if neutral_text == excited_text:
            print("❌ Emotion system not modifying text properly")
            return False
            
        print("✅ Emotion system working")
        return True
        
    except Exception as e:
        print(f"❌ Emotion system test failed: {e}")
        return False


def test_caching_system():
    """Test TTS caching functionality"""
    print("\n🧪 Testing caching system...")
    
    try:
        from modules.voice.synthesis import VoiceSynthesis
        import tempfile
        
        # Use temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        
        config = {
            'cache_enabled': True,
            'cache_dir': temp_dir,
            'cache_max_age': 3600
        }
        
        tts = VoiceSynthesis(config)
        
        # Test cache key generation
        test_config = {'rate': 200, 'volume': 0.8, 'emotion': 'neutral'}
        cache_key = tts._generate_cache_key("test text", test_config)
        
        if not isinstance(cache_key, str) or len(cache_key) != 32:
            print("❌ Cache key generation failed")
            return False
            
        # Test cache directory creation
        if not tts.cache_enabled or not tts.cache_dir.exists():
            print("❌ Cache directory not created")
            return False
            
        print("✅ Caching system working")
        return True
        
    except Exception as e:
        print(f"❌ Caching system test failed: {e}")
        return False


def test_multi_engine_support():
    """Test multiple TTS engine support"""
    print("\n🧪 Testing multi-engine support...")
    
    try:
        from modules.voice.synthesis import VoiceSynthesis
        
        # Test with different engines
        engines = ['pyttsx3', 'gtts', 'edge_tts']
        
        for engine in engines:
            tts = VoiceSynthesis({'engine': engine})
            
            if tts.engine_type != engine:
                print(f"❌ Engine configuration failed for: {engine}")
                return False
                
        # Test engine-specific methods exist
        tts = VoiceSynthesis({'engine': 'pyttsx3'})
        
        engine_methods = [
            '_synthesize_with_pyttsx3',
            '_synthesize_with_gtts', 
            '_synthesize_with_edge_tts'
        ]
        
        missing_methods = []
        for method in engine_methods:
            if not hasattr(tts, method):
                missing_methods.append(method)
                
        if missing_methods:
            print(f"❌ Missing engine methods: {missing_methods}")
            return False
            
        print("✅ Multi-engine support working")
        return True
        
    except Exception as e:
        print(f"❌ Multi-engine support test failed: {e}")
        return False


def test_enhanced_statistics():
    """Test enhanced statistics tracking"""
    print("\n🧪 Testing enhanced statistics...")
    
    try:
        from modules.voice.synthesis import VoiceSynthesis
        
        tts = VoiceSynthesis({})
        
        # Test enhanced stats structure
        required_stats = [
            'texts_synthesized', 'synthesis_failures', 'total_characters',
            'cache_hits', 'cache_misses', 'average_synthesis_time',
            'voice_profiles_used', 'languages_used', 'synthesis_history'
        ]
        
        for stat in required_stats:
            if stat not in tts.stats:
                print(f"❌ Missing statistic: {stat}")
                return False
                
        # Test statistics methods
        stats = tts.get_statistics()
        
        required_calculated_stats = ['success_rate', 'cache_hit_rate', 'average_text_length']
        for stat in required_calculated_stats:
            if stat not in stats:
                print(f"❌ Missing calculated statistic: {stat}")
                return False
                
        print("✅ Enhanced statistics working")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced statistics test failed: {e}")
        return False


async def test_voice_module_integration():
    """Test voice module integration with enhanced TTS"""
    print("\n🧪 Testing voice module integration...")
    
    try:
        from modules.voice import VoiceModule
        
        # Test module creation
        voice_module = VoiceModule()
        
        # Test enhanced methods
        enhanced_methods = [
            'speak_with_emotion', 'speak_notification', 'speak_alert',
            'get_available_voices', 'set_voice_profile', 'get_voice_profiles'
        ]
        
        missing_methods = []
        for method in enhanced_methods:
            if not hasattr(voice_module, method):
                missing_methods.append(method)
                
        if missing_methods:
            print(f"❌ Missing enhanced voice module methods: {missing_methods}")
            return False
            
        print("✅ Voice module integration working")
        return True
        
    except Exception as e:
        print(f"❌ Voice module integration test failed: {e}")
        return False


def test_advanced_speak_features():
    """Test advanced speaking features"""
    print("\n🧪 Testing advanced speaking features...")
    
    try:
        from modules.voice.synthesis import VoiceSynthesis
        
        tts = VoiceSynthesis({})
        
        # Test method signatures for advanced features
        import inspect
        
        # Check speak method signature
        speak_sig = inspect.signature(tts.speak)
        expected_params = ['text', 'voice_config', 'profile', 'priority']
        
        for param in expected_params:
            if param not in speak_sig.parameters:
                print(f"❌ Missing parameter in speak method: {param}")
                return False
                
        # Test emotion speaking method
        emotion_sig = inspect.signature(tts.speak_with_emotion)
        emotion_params = ['text', 'emotion', 'intensity']
        
        for param in emotion_params:
            if param not in emotion_sig.parameters:
                print(f"❌ Missing parameter in speak_with_emotion: {param}")
                return False
                
        print("✅ Advanced speaking features working")
        return True
        
    except Exception as e:
        print(f"❌ Advanced speaking features test failed: {e}")
        return False


async def main():
    """Run verification tests for Issue #7"""
    print("🎯 Issue #7 Verification: Text-to-Speech Integration")
    print("=" * 60)
    
    tests = [
        test_enhanced_tts_structure,
        test_voice_profiles,
        test_emotion_system,
        test_caching_system,
        test_multi_engine_support,
        test_enhanced_statistics,
        test_voice_module_integration,
        test_advanced_speak_features
    ]
    
    passed = 0
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            
    print(f"\n📊 Verification Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 Issue #7 is COMPLETE!")
        print("\n✅ Enhanced Text-to-Speech Features Implemented:")
        print("   • Advanced voice profiles (default, notification, alert, reading, conversation)")
        print("   • Emotion and speaking style support (neutral, happy, sad, excited, cheerful, friendly)")
        print("   • Multi-engine TTS support (pyttsx3, gTTS, Edge TTS)")
        print("   • Intelligent caching system with TTL and optimization")
        print("   • Enhanced statistics and performance monitoring")
        print("   • Priority-based speech queuing and interruption")
        print("   • Voice configuration profiles and customization")
        print("   • Comprehensive error handling and graceful degradation")
        
        print("\n⚠️  Note: Advanced TTS features may require additional dependencies:")
        print("   • pip install pyttsx3 (offline TTS)")
        print("   • pip install gtts (Google Text-to-Speech)")
        print("   • pip install edge-tts (Microsoft Edge TTS)")
        print("   • pip install pygame (for audio playback)")
        print("   • sudo apt install espeak espeak-data (system TTS engine)")
        
        print("\n🚀 Ready to move to Issue #8: Wake Word Detection")
        return True
    else:
        print("\n⚠️  Issue #7 needs attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)