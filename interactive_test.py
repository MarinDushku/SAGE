#!/usr/bin/env python3
"""
Interactive SAGE Test - Chat with SAGE and see learning in action
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def interactive_sage_test():
    """Interactive test with SAGE"""
    print("🤖 SAGE Interactive Test")
    print("=" * 40)
    print("Type 'quit' to exit")
    print()
    
    # Initialize modules
    from modules.nlp import NLPModule
    from modules.learning import LearningModule
    from modules.learning.learning_module import UserInteraction
    import time
    
    # Setup NLP
    nlp = NLPModule()
    nlp.config = {'enabled': True, 'llm': {'provider': 'ollama', 'model': 'phi3:mini'}}
    await nlp.initialize()
    
    # Setup Learning
    learning = LearningModule()  
    learning.config = {'enabled': True, 'command_optimization': True, 'preference_tracking': True}
    await learning.initialize()
    
    print("✅ SAGE systems initialized")
    print("🧠 Learning from your interactions...")
    print()
    
    conversation_count = 0
    
    try:
        while True:
            # Get user input
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
                
            if not user_input:
                continue
                
            conversation_count += 1
            start_time = time.time()
            
            # Analyze intent
            intent_result = await nlp.analyze_intent(user_input)
            
            # Get LLM response
            response = await nlp.process_text(user_input)
            
            if response.get('success'):
                response_text = response['response']['text']
                processing_time = time.time() - start_time
                
                print(f"SAGE: {response_text}")
                print()
                
                # Learn from this interaction
                interaction = UserInteraction(
                    timestamp=time.time(),
                    user_input=user_input,
                    intent=intent_result.get('intent', 'unknown'),
                    intent_confidence=intent_result.get('confidence', 0.0),
                    response=response_text,
                    success=True,
                    response_time=processing_time,
                    source_module='interactive_test'
                )
                
                await learning.learn_from_interaction(interaction)
                
                # Show learning stats every 3 interactions
                if conversation_count % 3 == 0:
                    status = learning.get_status()
                    stats = status.get('statistics', {})
                    cache_sizes = status.get('cache_sizes', {})
                    
                    print("📊 Learning Update:")
                    print(f"   Interactions: {cache_sizes.get('interactions', 0)}")
                    print(f"   Preferences: {cache_sizes.get('preferences', 0)}")  
                    print(f"   Patterns: {cache_sizes.get('patterns', 0)}")
                    print()
                    
            else:
                print(f"SAGE: Sorry, I encountered an error: {response.get('error')}")
                print()
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    # Show final learning insights
    print("\n📈 Final Learning Insights:")
    status = learning.get_status()
    stats = status.get('statistics', {})
    cache_sizes = status.get('cache_sizes', {})
    
    print(f"   Total interactions: {cache_sizes.get('interactions', 0)}")
    print(f"   Preferences learned: {cache_sizes.get('preferences', 0)}")
    print(f"   Command patterns: {cache_sizes.get('patterns', 0)}")
    
    # Show some learned preferences
    preferences = await learning.get_user_preferences()
    if preferences:
        print("\n👤 Some learned preferences:")
        for i, (pref_id, pref_data) in enumerate(list(preferences.items())[:3]):
            if isinstance(pref_data, dict):
                category = pref_data.get('category', 'unknown')
                value = pref_data.get('value', 'unknown')
                print(f"   {category}: {value}")
    
    # Cleanup
    await nlp.shutdown()
    await learning.shutdown()
    
    print("\n✅ SAGE session completed. Learning data saved!")

if __name__ == "__main__":
    asyncio.run(interactive_sage_test())