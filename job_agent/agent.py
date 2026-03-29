from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters
import os
import sys
import traceback

sys.stderr.write("\n" + "="*60 + "\n")
sys.stderr.write("AGENT INITIALIZATION\n")
sys.stderr.write("="*60 + "\n")

from dotenv import load_dotenv

# Only load .env in local development, not in Cloud Run
if os.path.exists(".env"):
    load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Don't crash if keys missing - Flask will handle the error
if not GOOGLE_API_KEY or not RAPIDAPI_KEY:
    sys.stderr.write("WARNING: Missing API keys - agent will not work\n")
    sys.stderr.write(f"GOOGLE_API_KEY: {'set' if GOOGLE_API_KEY else 'MISSING'}\n")
    sys.stderr.write(f"RAPIDAPI_KEY: {'set' if RAPIDAPI_KEY else 'MISSING'}\n")

# Path to MCP server
mcp_server_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "mcp_job_server",
    "server.py"
)

sys.stderr.write(f"MCP Path: {mcp_server_path}\n")

# Initialize McpToolset with correct parameters
tools_list = []
sys.stderr.write("\nInitializing McpToolset...\n")

try:
    # Prepare environment variables for MCP server subprocess
    mcp_env = os.environ.copy()
    mcp_env["GOOGLE_API_KEY"] = GOOGLE_API_KEY
    mcp_env["RAPIDAPI_KEY"] = RAPIDAPI_KEY

    # Create StdioServerParameters for the MCP server
    # IMPORTANT: Use absolute path to server.py
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[mcp_server_path],
        env=mcp_env
    )

    # Create StdioConnectionParams wrapper
    connection_params = StdioConnectionParams(server_params=server_params)

    # Create McpToolset with connection_params
    mcp_toolset = McpToolset(connection_params=connection_params)
    tools_list = [mcp_toolset]
    sys.stderr.write("OK - McpToolset initialized\n")
except Exception as e:
    sys.stderr.write(f"ERROR Failed: {type(e).__name__}: {str(e)}\n")
    sys.stderr.write("Traceback:\n")
    for line in traceback.format_exc().split('\n'):
        if line.strip():
            sys.stderr.write(f"  {line}\n")

sys.stderr.write(f"Tools count: {len(tools_list)}\n")

# Create agent
root_agent = LlmAgent(
    name="job_agent",
    model="gemini-2.5-flash",
    tools=tools_list,
    instruction="""You are a Job Intelligence Agent. ALWAYS call search_jobs tool to find jobs."""
)

sys.stderr.write("OK - Agent ready\n")
sys.stderr.write("="*60 + "\n\n")
















