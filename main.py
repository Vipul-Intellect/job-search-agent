#!/usr/bin/env python3
"""
Cloud Run entry point for Job Search Agent
Provides HTTP API for job search queries
"""

import os
import json
import asyncio
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def normalize_query(text: str) -> str:
    """Normalize query by removing extra spaces"""
    return " ".join(text.split()).strip()

@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "Job Search Agent",
        "version": "1.0"
    })

@app.route("/search", methods=["POST"])
def search_jobs():
    """
    Search for jobs using the agent.

    Expected JSON body:
    {
        "query": "ML Engineer in Bangalore"
    }

    Returns:
    {
        "success": true/false,
        "query": "user query",
        "results": [job objects],
        "count": number
    }
    """
    try:
        # Lazy-load agent only when needed
        from job_agent.agent import root_agent
        from google.adk.agents import InvocationContext

        data = request.get_json() or {}
        query = data.get("query", "").strip()

        if not query:
            return jsonify({
                "success": False,
                "error": "Missing 'query' field in request body"
            }), 400

        logger.info(f"Processing job search query: {query}")

        # Normalize query
        normalized_query = normalize_query(query)

        # Create invocation context for the agent
        context = InvocationContext()

        # Collect all events from the agent
        all_events = []
        result_data = None

        async def run_agent():
            """Run the agent and collect results"""
            nonlocal all_events, result_data

            try:
                async for event in root_agent.run_async(context):
                    all_events.append(event)
                    logger.debug(f"Agent event: {type(event).__name__}")

                    # Check if this is a tool result with job data
                    if hasattr(event, 'result') and event.result:
                        try:
                            if isinstance(event.result, dict):
                                result_data = event.result
                            elif isinstance(event.result, str):
                                result_data = json.loads(event.result)
                        except:
                            logger.warning("Could not parse event result as JSON")

            except Exception as e:
                logger.error(f"Error running agent: {type(e).__name__}: {str(e)}")
                raise

        # Run the agent with asyncio
        try:
            asyncio.run(run_agent())
        except RuntimeError as e:
            if "asyncio.run() cannot be called from a running event loop" in str(e):
                # If we're already in an event loop, try with a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(run_agent())
                    finally:
                        loop.close()
            else:
                raise

        # Format response
        if result_data:
            if isinstance(result_data, dict) and result_data.get("success"):
                # MCP server returned structured job data
                return jsonify({
                    "success": True,
                    "query": query,
                    "results": result_data.get("jobs", []),
                    "count": result_data.get("count", 0),
                    "agent_events": len(all_events)
                })
            else:
                # Return whatever the agent produced
                return jsonify({
                    "success": False,
                    "query": query,
                    "agent_response": result_data,
                    "agent_events": len(all_events)
                })
        else:
            # No structured results, return agent event info
            return jsonify({
                "success": False,
                "query": query,
                "message": "Agent processed query but returned no structured results",
                "agent_events": len(all_events),
                "events": [str(type(e).__name__) for e in all_events]
            })

    except Exception as e:
        logger.error(f"Search endpoint error: {type(e).__name__}: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }), 500

@app.route("/search", methods=["GET"])
def search_jobs_get():
    """Allow GET requests with query parameter"""
    query = request.args.get("query", "").strip()

    if not query:
        return jsonify({
            "success": False,
            "error": "Missing 'query' parameter"
        }), 400

    # Convert GET to POST
    return search_jobs()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("FLASK_ENV") == "development"

    logger.info(f"Starting Job Search Agent on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
