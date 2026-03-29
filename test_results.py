#!/usr/bin/env python3
"""Test agent returns actual job results"""

import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    from job_agent.agent import root_agent
    from google.adk.agents import InvocationContext

    print("\n" + "="*60)
    print("TESTING JOB SEARCH AGENT")
    print("="*60 + "\n")

    # Create context
    context = InvocationContext()

    # Track results
    job_results = None
    all_responses = []

    print("Running agent query: 'Find ML Engineer jobs in Bangalore'\n")

    try:
        # Run agent - it will stream events
        async for event in root_agent.run_async(context):
            event_type = type(event).__name__
            print(f"Event: {event_type}")

            # Check for tool results or model responses
            if hasattr(event, 'result'):
                if event.result:
                    print(f"  Result: {event.result}\n")
                    all_responses.append(event.result)

                    # Try to parse as JSON for job data
                    try:
                        if isinstance(event.result, str):
                            parsed = json.loads(event.result)
                            if isinstance(parsed, dict) and 'jobs' in parsed:
                                job_results = parsed
                                print(f"  Found {len(parsed.get('jobs', []))} jobs!\n")
                    except:
                        pass

            # Check for text content
            if hasattr(event, 'content'):
                print(f"  Content: {event.content}\n")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

    print("="*60)
    if job_results:
        print(f"SUCCESS: Got {len(job_results.get('jobs', []))} jobs")
        print(f"Jobs: {json.dumps(job_results, indent=2)}")
    else:
        print("WARNING: No structured job results returned")
        if all_responses:
            print(f"Responses received: {all_responses}")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
