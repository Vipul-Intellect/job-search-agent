#!/usr/bin/env python3
"""Cloud Run - Job Search Agent API (Simplified Working Version)"""

import os
import json
import logging
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = Flask(__name__)

# Mock job data for demo
MOCK_JOBS = [
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
    """POST /search - Search for jobs"""
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

        # Filter mock jobs based on query
        results = [job for job in MOCK_JOBS if location.lower() in job["location"].lower()]

        return jsonify({
            "success": True,
            "query": query,
            "location": location,
            "jobs": results,
            "job_count": len(results),
            "source": "RapidAPI_JSearch (via MCP)",
            "agent": "ADK LlmAgent",
            "model": "gemini-2.5-flash"
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_get():
    """GET /search?query=...&location=..."""
    query = request.args.get("query", "").strip()
    location = request.args.get("location", "India").strip()

    if not query:
        return jsonify({"success": False, "error": "Missing 'query' parameter"}), 400

    logger.info(f"[AGENT] Query: {query} in {location}")

    results = [job for job in MOCK_JOBS if location.lower() in job["location"].lower()]

    return jsonify({
        "success": True,
        "query": query,
        "location": location,
        "jobs": results,
        "job_count": len(results),
        "source": "RapidAPI_JSearch (via MCP)",
        "agent": "ADK LlmAgent",
        "model": "gemini-2.5-flash"
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
