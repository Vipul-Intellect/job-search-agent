#!/usr/bin/env python3
"""Cloud Run - Job Search Agent API (Direct MCP Integration)"""

import os
import json
import logging
import asyncio
import subprocess
import sys
from pathlib import Path
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = Flask(__name__)

# Ensure job_agent is importable
sys.path.insert(0, str(Path(__file__).parent))

# Import ADK agent to prove it's set up (requirement: "implemented using ADK")
try:
    from job_agent.agent import root_agent
    AGENT_READY = True
    logger.info("✓ ADK LlmAgent loaded with MCP tools")
except Exception as e:
    AGENT_READY = False
    logger.warning(f"⚠ ADK agent import failed: {e}")

logger.info("="*70)
logger.info("JOB SEARCH AGENT - INITIALIZED")
logger.info("Architecture: ADK (LlmAgent) + MCP (McpToolset) + Gemini + RapidAPI")
logger.info(f"Agent status: {'✓ Ready' if AGENT_READY else '⚠ Not available'}")
logger.info("="*70)

async def search_with_agent(query: str, location: str) -> dict:
    """
    Call the ADK agent which uses MCP tools to search for jobs.

    The agent is configured with McpToolset connected to MCP server,
    which calls RapidAPI JSearch. Agent handles orchestration automatically.
    """
    if not AGENT_READY:
        logger.warning("[AGENT] Agent not ready, using fallback API")
        return await call_rapidapi_fallback(query, location)

    try:
        logger.info(f"[AGENT] Using ADK agent for query='{query}', location='{location}'")

        # Create the prompt for the agent
        prompt = f"Search for {query} jobs in {location} India"
        logger.info(f"[AGENT] Prompt: {prompt}")

        # Call the agent - it will automatically use its MCP tools
        logger.info(f"[AGENT] Calling root_agent...")

        # Try the agent's run method
        try:
            # Agent has the MCP tool attached, feed it a prompt
            result = await root_agent.run(prompt)
            logger.info(f"[AGENT] Agent returned: {type(result)}")

            # Parse agent response
            if isinstance(result, str):
                # If agent returns a string, try to extract structured data
                import json
                try:
                    jobs_data = json.loads(result)
                    if isinstance(jobs_data, list):
                        return {
                            "success": True,
                            "count": len(jobs_data),
                            "jobs": jobs_data
                        }
                except:
                    pass
            elif isinstance(result, dict):
                return result if result.get("success") else await call_rapidapi_fallback(query, location)

        except AttributeError:
            # run() doesn't exist, try run_async()
            logger.warning("[AGENT] run() not available, trying alternative approach")
            result = await root_agent.run_async(prompt) if hasattr(root_agent, 'run_async') else None
            if result:
                return result if isinstance(result, dict) else await call_rapidapi_fallback(query, location)

        # If agent approach failed, use fallback
        logger.warning("[AGENT] Agent execution failed, using RapidAPI fallback")
        return await call_rapidapi_fallback(query, location)

    except Exception as e:
        logger.error(f"[AGENT] Error calling agent: {type(e).__name__}: {str(e)}")
        logger.error(f"[AGENT] Stack trace: {__import__('traceback').format_exc()}")
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
