#!/usr/bin/env python3
"""Quick test runner for the job search agent"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_agent():
    """Test agent with a job search query"""
    print("\n" + "="*60)
    print("TESTING AGENT")
    print("="*60 + "\n")

    from job_agent.agent import root_agent
    from google.adk.agents import InvocationContext

    query = "ML Engineer in Bangalore"
    print(f"Query: {query}\n")

    try:
        # Create invocation context
        context = InvocationContext()

        # Add user message to context - this is the query
        print(f"Running agent with query: {query}\n")

        # Run the agent
        events = []
        async for event in root_agent.run_async(context):
            events.append(event)
            print(f"Event: {event}")

        print(f"\nTotal events: {len(events)}")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())
