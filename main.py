#!/usr/bin/env python3
"""
Cloud Run - Job Search Agent API
Architecture: ADK LlmAgent + MCP McpToolset + Gemini + RapidAPI
"""

import os
import sys
import json
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api")

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=3)

# Global state
AGENT_READY = False
AGENT_ERROR = None
AGENT_INSTANCE = None

logger.info("="*70)
logger.info("JOB SEARCH AGENT - STARTING INITIALIZATION")
logger.info("="*70)

# ===== CHECK API KEYS AT STARTUP =====
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

if GOOGLE_KEY:
    logger.info("✓ GOOGLE_API_KEY found")
else:
    logger.warning("✗ GOOGLE_API_KEY NOT found")

if RAPIDAPI_KEY:
    logger.info("✓ RAPIDAPI_KEY found")
else:
    logger.warning("✗ RAPIDAPI_KEY NOT found")

# ===== LAZY LOAD AGENT =====
def get_agent():
    """Lazy-load and cache agent instance"""
    global AGENT_READY, AGENT_ERROR, AGENT_INSTANCE

    if AGENT_INSTANCE is not None:
        return AGENT_INSTANCE, AGENT_READY, AGENT_ERROR

    try:
        logger.info("Lazy-loading ADK agent...")

        # Check keys again
        if not GOOGLE_KEY or not RAPIDAPI_KEY:
            raise ValueError("API keys not set in environment")

        logger.info("Importing job_agent.agent...")
        from job_agent.agent import root_agent

        AGENT_INSTANCE = root_agent
        AGENT_READY = True
        logger.info("✓ Agent loaded and ready")

        return AGENT_INSTANCE, AGENT_READY, None

    except Exception as e:
        AGENT_ERROR = f"{type(e).__name__}: {str(e)}"
        logger.error(f"✗ Agent load failed: {AGENT_ERROR}")
        import traceback
        logger.error(traceback.format_exc())
        return None, False, AGENT_ERROR

# ===== AGENT EXECUTION =====
async def execute_agent(query: str, location: str) -> dict:
    """Execute agent query asynchronously"""
    logger.info(f"[AGENT] Query: {query} in {location}")

    try:
        agent, ready, error = get_agent()

        if not ready:
            logger.error(f"Agent not ready: {error}")
            return {"success": False, "error": f"Agent not ready: {error}"}

        if not agent:
            return {"success": False, "error": "Agent instance is None"}

        # Import InvocationContext
        from google.adk.agents import InvocationContext

        # Create context
        context = InvocationContext()

        # Collect events
        events = []
        responses = []
        jobs_data = None

        logger.info("[AGENT] Starting agent execution...")

        # Run agent
        async for event in agent.run_async(context):
            event_type = type(event).__name__
            events.append(event_type)

            logger.debug(f"[EVENT] {event_type}")

            # Try to extract results
            if hasattr(event, 'result') and event.result:
                logger.info(f"[RESULT] Found result in {event_type}")
                try:
                    if isinstance(event.result, dict):
                        jobs_data = event.result
                        logger.info(f"[RESULT] Got dict result: {type(event.result)}")
                    elif isinstance(event.result, str):
                        jobs_data = json.loads(event.result)
                        logger.info(f"[RESULT] Parsed JSON result")
                except Exception as parse_err:
                    logger.warning(f"[RESULT] Could not parse: {parse_err}")

            # Try to extract text response
            if hasattr(event, 'text') and event.text:
                responses.append(event.text)
                logger.info(f"[TEXT] Got text response: {event.text[:100]}...")

        logger.info(f"[AGENT] Completed with {len(events)} events")

        # Build response
        result = {
            "success": True,
            "query": query,
            "location": location,
            "events_count": len(events),
            "event_types": events
        }

        # Add job results if available
        if jobs_data:
            if isinstance(jobs_data, dict):
                if jobs_data.get("success"):
                    result["jobs"] = jobs_data.get("jobs", [])
                    result["job_count"] = jobs_data.get("count", 0)
                    result["source"] = "RapidAPI_JSearch"
                    logger.info(f"[SUCCESS] Returned {result['job_count']} jobs")
                else:
                    result["tool_error"] = jobs_data.get("error", "Unknown tool error")
            else:
                result["raw_data"] = str(jobs_data)[:500]

        if responses:
            result["agent_text"] = responses[0]

        return result

    except asyncio.TimeoutError:
        logger.error("[ERROR] Agent execution timed out")
        return {"success": False, "error": "Agent timeout (>120s)"}

    except Exception as e:
        logger.error(f"[ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def run_async_safe(coro):
    """Run async coroutine safely in new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=120))
    except asyncio.TimeoutError:
        return {"success": False, "error": "Request timeout"}
    finally:
        loop.close()

# ===== ROUTES =====

@app.route("/", methods=["GET"])
def root():
    """Root endpoint - health check"""
    agent, ready, error = get_agent()

    if ready:
        return jsonify({
            "status": "ready",
            "service": "Job Search Agent",
            "version": "2.0",
            "tech": "ADK + MCP + Gemini + RapidAPI",
            "endpoints": {
                "/": "This page",
                "/health": "Health check",
                "/search": "Job search (POST with JSON)",
                "/search?query=...&location=...": "Job search (GET)"
            }
        })
    else:
        return jsonify({
            "status": "error",
            "error": error or "Unknown error"
        }), 503

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    agent, ready, error = get_agent()
    return jsonify({
        "healthy": ready,
        "agent_ready": ready,
        "error": error if not ready else None
    })

@app.route("/search", methods=["POST"])
def search_post():
    """
    POST /search
    Body: {"query": "ML Engineer", "location": "Bangalore"}
    """
    try:
        # Parse request
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        location = data.get("location", "India").strip()

        if not query:
            return jsonify({
                "success": False,
                "error": "Missing 'query' field",
                "example": {"query": "ML Engineer", "location": "Bangalore"}
            }), 400

        logger.info(f"[REQUEST] POST /search - Query: {query}")

        # Execute agent in thread with timeout
        future = executor.submit(
            run_async_safe,
            execute_agent(query, location)
        )

        result = future.result(timeout=130)  # 130 sec (120 + buffer)
        return jsonify(result)

    except TimeoutError:
        return jsonify({
            "success": False,
            "error": "Request processing timeout"
        }), 504
    except Exception as e:
        logger.error(f"[ERROR] {type(e).__name__}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/search", methods=["GET"])
def search_get():
    """
    GET /search?query=ML Engineer&location=Bangalore
    """
    query = request.args.get("query", "").strip()
    location = request.args.get("location", "India").strip()

    if not query:
        return jsonify({
            "success": False,
            "error": "Missing 'query' parameter",
            "example": "/search?query=ML Engineer&location=Bangalore"
        }), 400

    logger.info(f"[REQUEST] GET /search - Query: {query}")

    # Execute agent in thread with timeout
    try:
        future = executor.submit(
            run_async_safe,
            execute_agent(query, location)
        )
        result = future.result(timeout=130)
        return jsonify(result)
    except TimeoutError:
        return jsonify({
            "success": False,
            "error": "Request timeout"
        }), 504
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not found",
        "available": ["/", "/health", "/search"]
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Server error",
        "details": str(e)
    }), 500

# ===== STARTUP =====

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))

    logger.info("="*70)
    logger.info(f"Starting Flask server on 0.0.0.0:{port}")
    logger.info("="*70)

    try:
        app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        logger.error(f"Failed to start: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
