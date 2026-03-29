# PowerShell Test Script for Job Search Agent
# This tests the agent directly without HTTP - pure ADK + MCP + Gemini flow

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Job Search Agent - Local Test" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Step 1: Activate venv
Write-Host "[1/4] Activating virtual environment..." -ForegroundColor Yellow
& "C:\Users\vtvip\genAi\job-search-agent\venv\Scripts\Activate.ps1"

# Step 2: Navigate to project
Write-Host "[2/4] Changing to project directory..." -ForegroundColor Yellow
cd "C:\Users\vtvip\genAi\job-search-agent"

# Step 3: Check if dependencies are installed
Write-Host "[3/4] Verifying dependencies..." -ForegroundColor Yellow
python -c "from google.adk.agents import LlmAgent; from google.adk.tools.mcp_tool import McpToolset; print('OK - ADK and MCP installed')" 2>&1

# Step 4: Create and run inline test
Write-Host "[4/4] Running agent test..." -ForegroundColor Yellow
Write-Host ""

python << 'PYTHON_EOF'
import sys
import asyncio
import json
from job_agent.agent import root_agent
from google.adk.agents import InvocationContext

async def test_query(query_text):
    """Test agent with a job search query"""
    print(f"\n{'='*60}")
    print(f"QUERY: {query_text}")
    print(f"{'='*60}\n")

    try:
        context = InvocationContext()

        # Run agent with MCP
        print("Agent running (ADK + MCP + Gemini)...\n")

        event_count = 0
        last_result = None

        async for event in root_agent.run_async(context):
            event_count += 1
            event_type = type(event).__name__

            # Print event type
            print(f"[Event {event_count}] {event_type}")

            # Check if this event has results
            if hasattr(event, 'result'):
                last_result = event.result
                if event.result:
                    print(f"  Result found: {type(event.result)}")
                    if isinstance(event.result, (dict, str)):
                        print(f"  Content preview: {str(event.result)[:200]}...")

        print(f"\n{'='*60}")
        print(f"TOTAL EVENTS: {event_count}")

        if last_result:
            print(f"FINAL RESULT: {json.dumps(last_result, indent=2)[:500]}")
        else:
            print("NO RESULTS RETURNED")

        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

# Run test queries
async def main():
    queries = [
        "ML Engineer in Bangalore",
        "Python Developer in Mumbai",
        "Data Scientist roles in Delhi"
    ]

    for query in queries:
        await test_query(query)
        await asyncio.sleep(1)  # 1 second between queries

asyncio.run(main())
PYTHON_EOF

Write-Host "`nTest complete!" -ForegroundColor Green
