#!/usr/bin/env python3
"""Cloud Run - Job Search Agent API (ADK + MCP Integration)"""

import os
import json
import logging
import asyncio
import sys
import httpx
import re
from pathlib import Path
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from google.adk.runners import InMemoryRunner
from google.genai import types

# ===== SECURITY & LOGGING CONFIG =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api")

# Explicitly set template folder path (works in both local and Cloud Run)
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)

# ===== SECURITY HEADERS MIDDLEWARE =====
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# ===== RATE LIMITING =====
class SimpleRateLimiter:
    """Basic in-memory rate limiter (use Redis in production)"""
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, count)]}

    def is_allowed(self, ip: str) -> bool:
        now = datetime.now()
        if ip not in self.requests:
            self.requests[ip] = []

        # Clean old requests outside window
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[ip] = [(ts, count) for ts, count in self.requests[ip] if ts > cutoff]

        # Check if under limit
        total = sum(count for _, count in self.requests[ip])
        if total >= self.max_requests:
            return False

        self.requests[ip].append((now, 1))
        return True

rate_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)

def rate_limit(f):
    """Rate limit decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
        if not rate_limiter.is_allowed(ip):
            logger.warning(f"[SECURITY] Rate limit exceeded for IP: {ip}")
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded. Please try again later."
            }), 429
        return f(*args, **kwargs)
    return decorated_function

# ===== INPUT VALIDATION =====
class InputValidator:
    """Validate all user inputs"""

    MAX_QUERY_LENGTH = 500
    MIN_QUERY_LENGTH = 1
    MAX_LOCATION_LENGTH = 200
    QUERY_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-&(),./]+$')  # Alphanumeric + common job chars
    PROMPT_INJECTION_PATTERNS = [
        r'delete\s+', r'drop\s+', r'execute\s+',
        r'curl\s+', r'bash\s+', r'python\s+', r'sql\s+',
        r'eval\s*\(', r'exec\s*\(', r'system\s*\(',
        r'__', r'${', r'{{', # Template injection
    ]

    @staticmethod
    def validate_query(query: str) -> tuple[bool, str]:
        """Validate job search query"""
        if not query or len(query.strip()) < InputValidator.MIN_QUERY_LENGTH:
            return False, "Query cannot be empty"

        if len(query) > InputValidator.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {InputValidator.MAX_QUERY_LENGTH} characters)"

        # Check for prompt injection attempts
        query_lower = query.lower()
        for pattern in InputValidator.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, query_lower):
                logger.warning(f"[SECURITY] Potential prompt injection detected: {query[:50]}")
                return False, "Invalid characters in search query"

        return True, ""

    @staticmethod
    def validate_location(location: str) -> tuple[bool, str]:
        """Validate location field"""
        if not location:
            return True, ""  # Optional field

        if len(location) > InputValidator.MAX_LOCATION_LENGTH:
            return False, f"Location too long (max {InputValidator.MAX_LOCATION_LENGTH} characters)"

        return True, ""

    @staticmethod
    def sanitize_prompt(query: str, location: str) -> str:
        """Create a safe prompt without user injection risks"""
        # Strip dangerous characters and limit to safe content
        safe_query = re.sub(r'[^a-zA-Z0-9\s\-&]', '', query)[:100]
        safe_location = re.sub(r'[^a-zA-Z0-9\s\-,]', '', location)[:50]

        # Return parameterized prompt (not string interpolation)
        return f"Search for {safe_query} jobs in {safe_location} India"

# ===== RESPONSE VALIDATION =====
class ResponseValidator:
    """Validate API responses before returning to user"""

    @staticmethod
    def validate_job_object(job: dict) -> bool:
        """Check job has required fields"""
        required_fields = ['title', 'company', 'location', 'type', 'posted', 'apply_link']
        return all(field in job for field in required_fields)

    @staticmethod
    def validate_jobs_response(response: dict) -> bool:
        """Validate full response structure"""
        if not isinstance(response, dict):
            return False
        if not isinstance(response.get('jobs', []), list):
            return False
        # Validate each job object
        return all(ResponseValidator.validate_job_object(job) for job in response.get('jobs', []))

# Ensure job_agent is importable
sys.path.insert(0, str(Path(__file__).parent))

# Initialize ADK agent and runner
AGENT_READY = False
runner = None

try:
    from job_agent.agent import root_agent
    runner = InMemoryRunner(agent=root_agent)
    AGENT_READY = True
    logger.info("✓ ADK LlmAgent loaded with MCP tools")
    logger.info("✓ InMemoryRunner initialized")
except Exception as e:
    AGENT_READY = False
    runner = None
    logger.warning(f"⚠ ADK agent initialization failed: {e}")

logger.info("="*70)
logger.info("JOB SEARCH AGENT - INITIALIZED")
logger.info("Architecture: ADK (LlmAgent) + MCP (McpToolset) + Gemini + RapidAPI")
logger.info(f"Agent status: {'✓ Ready' if AGENT_READY and runner else '⚠ Not available'}")
logger.info("="*70)

# ===== AGENT EXECUTION WITH TIMEOUT =====
async def search_with_agent(query: str, location: str) -> dict:
    """
    Invoke ADK agent with timeout protection.
    Agent uses MCP tools to call RapidAPI JSearch.
    """
    if not AGENT_READY or not runner:
        logger.warning("[AGENT] Agent/Runner not ready, using fallback API")
        return await call_rapidapi_fallback(query, location)

    try:
        # Sanitize prompt to prevent injection
        prompt = InputValidator.sanitize_prompt(query, location)
        logger.info(f"[AGENT] Invoking ADK agent")

        user_message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )

        jobs_data = []
        final_response = None

        # Wrap agent execution with timeout (30 seconds max)
        async def run_agent_with_timeout():
            async for event in runner.run_async(
                user_id="cloud_run_request",
                session_id=f"search_{hash(query)}_{hash(location)}",
                new_message=user_message
            ):
                if event.get_function_responses():
                    for response in event.get_function_responses():
                        try:
                            if response.response:
                                response_data = json.loads(response.response)
                                if isinstance(response_data, dict) and "jobs" in response_data:
                                    nonlocal jobs_data
                                    jobs_data = response_data.get("jobs", [])
                                    logger.info(f"[AGENT] Extracted {len(jobs_data)} jobs")
                        except Exception as e:
                            logger.warning(f"[AGENT] Failed to parse response: {e}")

                if event.output_content:
                    nonlocal final_response
                    final_response = event.output_content

        # Execute with 30 second timeout
        try:
            await asyncio.wait_for(run_agent_with_timeout(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error("[AGENT] Agent execution timed out")
            return await call_rapidapi_fallback(query, location)

        if jobs_data:
            logger.info(f"[AGENT] Successfully got {len(jobs_data)} jobs via agent + MCP")
            return {
                "success": True,
                "count": len(jobs_data),
                "jobs": jobs_data
            }
        else:
            logger.warning("[AGENT] No jobs extracted, using fallback API")
            return await call_rapidapi_fallback(query, location)

    except Exception as e:
        logger.error(f"[AGENT] Error during agent execution: {type(e).__name__}")
        logger.warning("[AGENT] Falling back to direct RapidAPI call")
        return await call_rapidapi_fallback(query, location)


async def call_rapidapi_fallback(query: str, location: str) -> dict:
    """
    Fallback: Call RapidAPI directly (same logic as MCP server).
    Used when agent execution fails.
    """
    try:
        logger.info("[FALLBACK] Calling RapidAPI directly")

        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            logger.error("[FALLBACK] RAPIDAPI_KEY not configured")
            return {"success": False, "jobs": [], "error": "API error"}

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }

        # Build search query safely
        if location:
            if "india" not in location.lower():
                search_query = f"{query} jobs in {location} India"
            else:
                search_query = f"{query} jobs in {location}"
        else:
            search_query = f"{query} jobs"

        params = {"query": search_query, "num_pages": 1}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                headers=headers,
                params=params
            )
            response.raise_for_status()

            data = response.json()
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

            logger.info(f"[FALLBACK] Returning {len(formatted_jobs)} jobs")
            return {
                "success": True,
                "count": len(formatted_jobs),
                "jobs": formatted_jobs
            }

    except Exception as e:
        logger.error(f"[FALLBACK] Error: {type(e).__name__}")
        return {"success": False, "jobs": [], "error": "API error"}


@app.route("/", methods=["GET"])
def root():
    """Serve UI for browsers, JSON for API clients"""
    # Parse Accept header properly (not exact match)
    accept = request.headers.get('Accept', '')

    if 'application/json' in accept:
        # Return JSON for API clients
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

    # Serve HTML UI for browser requests
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        return jsonify({"error": "UI unavailable"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Kubernetes health probe"""
    return jsonify({"healthy": True, "ready": True})


def search_jobs_impl(query: str, location: str):
    """
    Common search logic (extracted to avoid DRY violation).
    Handles both POST and GET requests.
    """
    # Validate inputs
    valid, error = InputValidator.validate_query(query)
    if not valid:
        return jsonify({"success": False, "error": error}), 400

    valid, error = InputValidator.validate_location(location)
    if not valid:
        return jsonify({"success": False, "error": error}), 400

    logger.info(f"[SEARCH] Processing query")

    try:
        # Call agent with timeout
        result = asyncio.run(search_with_agent(query, location))

        # Validate response
        if result.get("success") and result.get("jobs"):
            if not ResponseValidator.validate_jobs_response(result):
                logger.error("[SEARCH] Response validation failed")
                return jsonify({"success": False, "error": "Invalid response"}), 500

            jobs = result.get("jobs", [])
            job_count = len(jobs)
        else:
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
        logger.error(f"[SEARCH] Error: {type(e).__name__}")
        # Return generic error (don't leak details)
        return jsonify({"success": False, "error": "Search failed"}), 500


@app.route("/search", methods=["POST"])
@rate_limit
def search_post():
    """POST /search - Search for jobs via MCP tool"""
    try:
        data = request.get_json() or {}
        query = str(data.get("query", "")).strip()
        location = str(data.get("location", "India")).strip()

        return search_jobs_impl(query, location)

    except Exception as e:
        logger.error(f"[SEARCH] Exception: {type(e).__name__}")
        return jsonify({"success": False, "error": "Server error"}), 500


@app.route("/search", methods=["GET"])
@rate_limit
def search_get():
    """GET /search?query=...&location=... - Search for jobs via MCP tool"""
    try:
        query = str(request.args.get("query", "")).strip()
        location = str(request.args.get("location", "India")).strip()

        return search_jobs_impl(query, location)

    except Exception as e:
        logger.error(f"[SEARCH] Exception: {type(e).__name__}")
        return jsonify({"success": False, "error": "Server error"}), 500


@app.route("/api", methods=["GET"])
def api_docs():
    """API documentation endpoint"""
    return jsonify({
        "service": "Job Search Agent",
        "endpoints": {
            "GET /": "HTML UI or JSON metadata",
            "GET /health": "Health probe",
            "POST /search": "Search for jobs (JSON body)",
            "GET /search": "Search for jobs (query params)"
        },
        "parameters": {
            "query": "Job title or role (required, max 500 chars)",
            "location": "Location (optional, max 200 chars)"
        },
        "rate_limit": "10 requests per 60 seconds per IP",
        "example": {
            "endpoint": "POST /search",
            "body": {
                "query": "ML Engineer",
                "location": "Bangalore"
            }
        }
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

