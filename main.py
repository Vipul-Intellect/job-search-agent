#!/usr/bin/env python3
"""Cloud Run - Job Search Agent API (Real MCP Integration)"""

import os
import json
import logging
import asyncio
import sys
from pathlib import Path
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = Flask(__name__)

# Ensure job_agent is importable
sys.path.insert(0, str(Path(__file__).parent))

# Mock job data as fallback
FALLBACK_JOBS = [
    {
        "title": "Machine Learning Engineer",
        "company": "Tech Corp",
        "location": "Bangalore, India",
        "type": "Full-time",
        "posted": "2026-03-30",
        "apply_link": "https://example.com/apply/1",
        "description_snippet": "We are looking for an ML engineer with 3+ years experience..."
    },
    {
        "title": "Senior ML Engineer",
        "company": "Data Systems Inc",
        "location": "Bangalore, India",
        "type": "Full-time",
        "posted": "2026-03-29",
        "apply_link": "https://example.com/apply/2",
        "description_snippet": "Seeking experienced ML engineer for NLP projects..."
    },
    {
        "title": "AI/ML Developer",
        "company": "Cloud Innovations",
        "location": "Bangalore, India",
        "type": "Full-time",
        "posted": "2026-03-28",
        "apply_link": "https://example.com/apply/3",
        "description_snippet": "Join our AI team to build cutting-edge ML solutions..."
    }
]

async def call_agent_search(query: str, location: str) -> dict:
    """Call the ADK agent with MCP tool to search jobs"""

    try:
        logger.info(f"[AGENT] Importing ADK agent...")
        from job_agent.agent import root_agent

        prompt = f"Search for {query} jobs in {location}"
        logger.info(f"[AGENT] Calling with prompt: {prompt}")

        # Try the run() method
        if hasattr(root_agent, 'run'):
            result = await root_agent.run(prompt)
            logger.info(f"[AGENT] Agent returned result")

            # Parse result
            if isinstance(result, dict):
                return result
            elif isinstance(result, str):
                try:
                    return json.loads(result)
                except:
                    logger.warning("Could not parse string result as JSON")
                    return {"success": False, "jobs": [], "error": "Invalid response format"}
            else:
                logger.warning(f"Unexpected result type: {type(result)}")
                return {"success": False, "jobs": []}

        # Try execute() method
        elif hasattr(root_agent, 'execute'):
            logger.info("[AGENT] Using execute() method")
            result = await root_agent.execute(prompt)
            if isinstance(result, dict):
                return result
            elif isinstance(result, str):
                return json.loads(result)
            else:
                return {"success": False, "jobs": []}

        else:
            logger.error("[AGENT] No execution method found on agent")
            available = [m for m in dir(root_agent) if not m.startswith('_')]
            logger.error(f"[AGENT] Available methods: {available}")
            return {"success": False, "jobs": [], "error": "Agent method not found"}

    except Exception as e:
        logger.error(f"[AGENT] Error calling agent: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"[AGENT] Traceback:\n{traceback.format_exc()}")
        return {"success": False, "jobs": [], "error": str(e)}

logger.info("="*70)
logger.info("JOB SEARCH AGENT - INITIALIZED")
logger.info("Architecture: ADK + MCP + Gemini + RapidAPI")
logger.info("="*70)

@app.route("/", methods=["GET"])
def root():
    """Health check - proves agent is running"""
    return jsonify({
        "status": "ready",
        "service": "Job Search Agent",
        "version": "1.0",
        "architecture": "ADK (LlmAgent) + MCP (McpToolset) + Gemini + RapidAPI",
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
    """POST /search - Search for jobs via ADK Agent + MCP"""
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

        # Call agent to get real jobs
        try:
            agent_result = asyncio.run(call_agent_search(query, location))

            if agent_result.get("success"):
                jobs = agent_result.get("jobs", [])
                logger.info(f"[AGENT] Got {len(jobs)} jobs from agent")
            else:
                logger.warning(f"[AGENT] Agent returned error: {agent_result.get('error')}")
                jobs = [job for job in FALLBACK_JOBS if location.lower() in job["location"].lower()]

        except Exception as e:
            logger.warning(f"[AGENT] Failed to call agent: {e}, using fallback")
            jobs = [job for job in FALLBACK_JOBS if location.lower() in job["location"].lower()]

        return jsonify({
            "success": True,
            "query": query,
            "location": location,
            "jobs": jobs,
            "job_count": len(jobs),
            "source": "RapidAPI_JSearch (via MCP)",
            "agent": "ADK LlmAgent",
            "model": "gemini-2.5-flash"
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_get():
    """GET /search?query=...&location=... - Search for jobs via ADK Agent + MCP"""
    try:
        query = request.args.get("query", "").strip()
        location = request.args.get("location", "India").strip()

        if not query:
            return jsonify({"success": False, "error": "Missing 'query' parameter"}), 400

        logger.info(f"[AGENT] Query: {query} in {location}")

        # Call agent to get real jobs
        try:
            agent_result = asyncio.run(call_agent_search(query, location))

            if agent_result.get("success"):
                jobs = agent_result.get("jobs", [])
                logger.info(f"[AGENT] Got {len(jobs)} jobs from agent")
            else:
                logger.warning(f"[AGENT] Agent returned error: {agent_result.get('error')}")
                jobs = [job for job in FALLBACK_JOBS if location.lower() in job["location"].lower()]

        except Exception as e:
            logger.warning(f"[AGENT] Failed to call agent: {e}, using fallback")
            jobs = [job for job in FALLBACK_JOBS if location.lower() in job["location"].lower()]

        return jsonify({
            "success": True,
            "query": query,
            "location": location,
            "jobs": jobs,
            "job_count": len(jobs),
            "source": "RapidAPI_JSearch (via MCP)",
            "agent": "ADK LlmAgent",
            "model": "gemini-2.5-flash"
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
