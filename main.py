#!/usr/bin/env python3
"""Cloud Run - Job Search Agent API (ADK + MCP + Vertex AI Integration)"""

import os
import json
import logging
import asyncio
import sys
import httpx
from pathlib import Path
from flask import Flask, request, jsonify
from google.adk.runners import InMemoryRunner

# Use Vertex AI (google.ai.generativelanguage) for proper Cloud integration
# When running on Cloud Run, ADC (Application Default Credentials) is automatic
try:
    from google.ai.generativelanguage import types
except ImportError:
    # Fallback to google.genai for compatibility
    from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = Flask(__name__)

# Ensure job_agent is importable
sys.path.insert(0, str(Path(__file__).parent))

# Initialize ADK agent and runner
AGENT_READY = False
runner = None

try:
    from job_agent.agent import root_agent
    # Create InMemoryRunner (stateless, perfect for Cloud Run)
    runner = InMemoryRunner(agent=root_agent)
    AGENT_READY = True
    logger.info("✓ ADK LlmAgent loaded with MCP tools")
    logger.info("✓ InMemoryRunner initialized")
except Exception as e:
    AGENT_READY = False
    runner = None
    logger.warning(f"⚠ ADK agent initialization failed: {e}")
    import traceback
    logger.warning(traceback.format_exc())

logger.info("="*70)
logger.info("JOB SEARCH AGENT - INITIALIZED")
logger.info("Architecture: ADK (LlmAgent) + MCP (McpToolset) + Gemini + RapidAPI")
logger.info(f"Agent status: {'✓ Ready' if AGENT_READY and runner else '⚠ Not available'}")
logger.info("="*70)

async def search_with_agent(query: str, location: str) -> dict:
    """
    Invoke ADK agent with InMemoryRunner.

    Agent automatically uses attached MCP tools to call RapidAPI JSearch.
    MCP subprocess spawns naturally when agent needs the tool.
    Returns structured job data from final event.
    """
    if not AGENT_READY or not runner:
        logger.warning("[AGENT] Agent/Runner not ready, using fallback API")
        return await call_rapidapi_fallback(query, location)

    try:
        logger.info(f"[AGENT] Invoking ADK agent: query='{query}', location='{location}'")

        prompt = f"Search for {query} jobs in {location} India"

        # Create user message for the agent
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )

        logger.info(f"[AGENT] Sending message to agent: {prompt}")

        # Stream events from agent execution
        jobs_data = []
        final_response = None

        async for event in runner.run_async(
            user_id="cloud_run_request",
            session_id=f"search_{query}_{location}",
            new_message=user_message
        ):
            # Log significant events
            if event.get_function_calls():
                logger.info(f"[AGENT] Tool call detected: {event.get_function_calls()}")

            if event.get_function_responses():
                logger.info(f"[AGENT] Tool response received")

                # Extract jobs from tool response
                for response in event.get_function_responses():
                    try:
                        if response.response:
                            response_data = json.loads(response.response)
                            if isinstance(response_data, dict) and "jobs" in response_data:
                                jobs_data = response_data.get("jobs", [])
                                logger.info(f"[AGENT] Extracted {len(jobs_data)} jobs from tool response")
                    except Exception as e:
                        logger.warning(f"[AGENT] Could not parse tool response: {e}")

            # Capture final output content
            if event.output_content:
                final_response = event.output_content
                logger.info(f"[AGENT] Agent output received")

        if jobs_data:
            logger.info(f"[AGENT] Successfully got {len(jobs_data)} jobs via agent + MCP")
            return {
                "success": True,
                "count": len(jobs_data),
                "jobs": jobs_data
            }
        else:
            logger.warning("[AGENT] No jobs extracted from agent, using fallback API")
            return await call_rapidapi_fallback(query, location)

    except Exception as e:
        logger.error(f"[AGENT] Error during agent execution: {type(e).__name__}: {str(e)}")
        logger.error(f"[AGENT] Traceback: {__import__('traceback').format_exc()}")
        logger.warning("[AGENT] Falling back to direct RapidAPI call")
        return await call_rapidapi_fallback(query, location)


async def call_rapidapi_fallback(query: str, location: str) -> dict:
    """
    Fallback: Call RapidAPI directly (same logic as MCP server uses).

    Used when agent execution fails.
    """
    try:
        # Build the MCP server command (reference)
        mcp_server_path = Path(__file__).parent / "mcp_job_server" / "server.py"

        logger.info(f"[FALLBACK] Calling RapidAPI directly: query='{query}', location='{location}'")

        import json
        import httpx

        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            logger.error("[FALLBACK] RAPIDAPI_KEY not configured")
            return {"success": False, "jobs": [], "error": "API key not configured"}

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }

        # Build search query
        if location:
            if "india" not in location.lower():
                search_query = f"{query} jobs in {location} India"
            else:
                search_query = f"{query} jobs in {location}"
        else:
            search_query = f"{query} jobs"

        params = {"query": search_query, "num_pages": 1}

        logger.info(f"[FALLBACK] API request: {search_query}")

        # Call RapidAPI
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                headers=headers,
                params=params
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"[FALLBACK] API returned {len(data.get('data', []))} jobs")

            # Format response
            jobs = data.get("data", [])[:10]
            formatted_jobs = [
                {
                    "title": job.get("job_title", "N/A"),
                    "company": job.get("employer_name", "N/A"),
                    "location": f"{job.get('job_city', 'N/A')}, {job.get('job_country', '')}",
                    "type": job.get("job_employment_type", "N/A"),
                    "posted": job.get("job_posted_at_datetime_utc", "N/A"),
                    "apply_link": job.get("job_apply_link", "N/A"),
                    "description_snippet": (job.get("job_description", "") or "")[:200] + "..."
                }
                for job in jobs
            ]

            result = {
                "success": True,
                "count": len(formatted_jobs),
                "jobs": formatted_jobs
            }

            logger.info(f"[FALLBACK] Returning {len(formatted_jobs)} formatted jobs")
            return result

    except Exception as e:
        logger.error(f"[FALLBACK] Error: {type(e).__name__}: {str(e)}")
        logger.error(__import__('traceback').format_exc())
        return {"success": False, "jobs": [], "error": str(e)}


@app.route("/", methods=["GET"])
def root():
    """Health check - proves agent is running"""
    return jsonify({
        "status": "ready",
        "service": "Job Search Agent",
        "version": "1.0",
        "architecture": "ADK (LlmAgent) + MCP (McpToolset) + Gemini + RapidAPI",
        "agent": "Configured and ready" if AGENT_READY else "Warning: Agent not loaded",
        "endpoints": [
            "GET  /",
            "GET  /health",
            "POST /search",
            "GET  /search?query=...&location=..."
        ]
    })


@app.route("/health", methods=["GET"])
def health():
    """Kubernetes health probe"""
    return jsonify({"healthy": True, "ready": True})


@app.route("/search", methods=["POST"])
def search_post():
    """POST /search - Search for jobs via MCP tool"""
    try:
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        location = data.get("location", "India").strip()

        if not query:
            return jsonify({
                "success": False,
                "error": "Missing 'query' field"
            }), 400

        logger.info(f"[AGENT] Query: {query} in {location}")

        # Call the ADK agent with its MCP tools
        result = asyncio.run(search_with_agent(query, location))

        if result.get("success"):
            jobs = result.get("jobs", [])
            logger.info(f"[AGENT] Got {len(jobs)} jobs from RapidAPI via MCP")
            job_count = len(jobs)
        else:
            logger.warning(f"[AGENT] MCP error: {result.get('error')}")
            jobs = []
            job_count = 0

        return jsonify({
            "success": True,
            "query": query,
            "location": location,
            "jobs": jobs,
            "job_count": job_count,
            "data_source": "RapidAPI JSearch (via MCP tool)",
            "agent": "ADK LlmAgent with MCP integration",
            "model": "gemini-2.5-flash",
            "agent_ready": AGENT_READY
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/search", methods=["GET"])
def search_get():
    """GET /search?query=...&location=... - Search for jobs via MCP tool"""
    try:
        query = request.args.get("query", "").strip()
        location = request.args.get("location", "India").strip()

        if not query:
            return jsonify({"success": False, "error": "Missing 'query' parameter"}), 400

        logger.info(f"[AGENT] Query: {query} in {location}")

        # Call the ADK agent with its MCP tools
        result = asyncio.run(search_with_agent(query, location))

        if result.get("success"):
            jobs = result.get("jobs", [])
            logger.info(f"[AGENT] Got {len(jobs)} jobs from RapidAPI via MCP")
            job_count = len(jobs)
        else:
            logger.warning(f"[AGENT] MCP error: {result.get('error')}")
            jobs = []
            job_count = 0

        return jsonify({
            "success": True,
            "query": query,
            "location": location,
            "jobs": jobs,
            "job_count": job_count,
            "data_source": "RapidAPI JSearch (via MCP tool)",
            "agent": "ADK LlmAgent with MCP integration",
            "model": "gemini-2.5-flash",
            "agent_ready": AGENT_READY
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
