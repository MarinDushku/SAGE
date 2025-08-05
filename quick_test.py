#!/usr/bin/env python3
"""
Quick test of stable version functionality
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import Logger
from modules.function_calling import FunctionRegistry

async def test_stable_version():
    """Test the stable version functionality"""
    logger = Logger("STABLE-TEST")
    main_log = logger.get_logger("test")
    
    # Initialize function calling system (same as stable version)
    function_registry = FunctionRegistry(
        logger.get_logger("functions"),
        None  # No calendar module - uses direct DB
    )
    
    print("🧪 Testing Stable Version Calendar Functions")
    print("=" * 50)
    
    # Test 1: Add event
    print("\n1️⃣ Adding event...")
    add_result = await function_registry.execute_function("add_calendar_event", {
        "title": "Test Meeting",
        "date": "tomorrow", 
        "time": "9am"
    })
    print(f"Add Result: {add_result}")
    
    # Test 2: Look up events
    print("\n2️⃣ Looking up events...")
    lookup_result = await function_registry.execute_function("lookup_calendar", {
        "date": "tomorrow"
    })
    print(f"Lookup Result: {lookup_result}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_stable_version())