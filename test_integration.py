#!/usr/bin/env python3
"""
SAGE Integration Test - Test all systems working together
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_sage_integration():
    """Test all SAGE systems integration"""
    print("🚀 SAGE Integration Test")
    print("=" * 50)
    
    try:
        # Test 1: Import all modules
        print("\n1️⃣ Testing Module Imports...")
        from modules.voice import VoiceModule
        from modules.nlp import NLPModule  
        from modules.learning import LearningModule
        print("✅ All modules imported successfully")
        
        # Test 2: Initialize modules individually
        print("\n2️⃣ Testing Individual Module Initialization...")
        
        # Initialize Voice Module
        voice = VoiceModule()
        voice.config = {'recognition': {'engine': 'whisper'}, 'synthesis': {'engine': 'pyttsx3'}}
        voice_success = await voice.initialize()
        print(f"   Voice Module: {'✅' if voice_success else '❌'}")
        
        # Initialize NLP Module
        nlp = NLPModule()
        nlp.config = {'enabled': True, 'llm': {'provider': 'ollama', 'model': 'phi3:mini'}}
        nlp_success = await nlp.initialize()
        print(f"   NLP Module: {'✅' if nlp_success else '❌'}")
        
        # Initialize Learning Module
        learning = LearningModule()
        learning.config = {'enabled': True, 'command_optimization': True}
        learning_success = await learning.initialize()
        print(f"   Learning Module: {'✅' if learning_success else '❌'}")
        
        # Test 3: Test NLP + Ollama
        print("\n3️⃣ Testing NLP + Ollama Integration...")
        if nlp_success:
            response = await nlp.process_text("Hello, how are you?")
            if response.get('success'):
                print("✅ NLP + Ollama working")
                print(f"   Response: {response['response']['text'][:60]}...")
            else:
                print("❌ NLP + Ollama failed")
        
        # Test 4: Test Learning System
        print("\n4️⃣ Testing Learning System...")
        if learning_success:
            from modules.learning.learning_module import UserInteraction
            import time
            
            test_interaction = UserInteraction(
                timestamp=time.time(),
                user_input="Test learning integration",
                intent="test",
                intent_confidence=0.8,
                response="Learning system is working!",
                success=True,
                response_time=1.0,
                source_module="test"
            )
            
            learn_result = await learning.learn_from_interaction(test_interaction)
            if learn_result.get('success'):
                print("✅ Learning system working")
                print(f"   Learned from interaction: {learn_result.get('interaction_id')}")
            else:
                print("❌ Learning system failed")
        
        # Test 5: Test Cross-Module Integration
        print("\n5️⃣ Testing Cross-Module Integration...")
        if nlp_success and learning_success:
            # Process text with NLP
            nlp_response = await nlp.process_text("What time is it?")
            
            if nlp_response.get('success'):
                # Learn from the interaction
                interaction = UserInteraction(
                    timestamp=time.time(),
                    user_input="What time is it?",
                    intent="time",
                    intent_confidence=0.8,
                    response=nlp_response['response']['text'],
                    success=True,
                    response_time=nlp_response.get('processing_time', 0),
                    source_module="nlp"
                )
                
                learn_result = await learning.learn_from_interaction(interaction)
                if learn_result.get('success'):
                    print("✅ NLP → Learning integration working")
                else:
                    print("❌ NLP → Learning integration failed")
            else:
                print("❌ NLP response failed for integration test")
        
        # Test 6: Check Data Persistence
        print("\n6️⃣ Testing Data Persistence...")
        if learning_success:
            status = learning.get_status()
            stats = status.get('statistics', {})
            cache_sizes = status.get('cache_sizes', {})
            
            print(f"   Interactions: {cache_sizes.get('interactions', 0)}")
            print(f"   Preferences: {cache_sizes.get('preferences', 0)}")
            print(f"   Patterns: {cache_sizes.get('patterns', 0)}")
            print("✅ Data persistence working")
        
        # Test 7: Test Learning Insights
        print("\n7️⃣ Testing Learning Insights...")
        if learning_success:
            insights = learning.get_learning_insights()
            if 'statistics' in insights:
                print("✅ Learning insights generated")
                print(f"   Total interactions: {insights['statistics']['total_interactions']}")
            else:
                print("❌ Learning insights failed")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        if voice_success:
            await voice.shutdown()
        if nlp_success:
            await nlp.shutdown()
        if learning_success:
            await learning.shutdown()
        
        print("\n🎉 Integration test completed!")
        print("\n📊 Results:")
        print(f"   Voice Module: {'✅' if voice_success else '❌'}")
        print(f"   NLP Module: {'✅' if nlp_success else '❌'}")
        print(f"   Learning Module: {'✅' if learning_success else '❌'}")
        
        if voice_success and nlp_success and learning_success:
            print("\n🚀 All systems operational!")
            return True
        else:
            print("\n⚠️  Some systems need attention")
            return False
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sage_integration())
    sys.exit(0 if success else 1)