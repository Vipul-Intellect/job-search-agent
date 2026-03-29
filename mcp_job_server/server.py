"""
MCP Server for Job Search using JSearch API (RapidAPI)
"""

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import httpx
import os
import json
import logging
from datetime import datetime, timedelta
import hashlib

# ===== CONFIG SECTION =====
API_TIMEOUT = 30.0
MAX_JOBS_RETURN = 10
CACHE_DURATION_HOURS = 1
API_ENDPOINT = "https://jsearch.p.rapidapi.com/search"

# ===== LOGGING SETUP =====
# CRITICAL: Log to file, NOT to stderr/stdout (breaks MCP protocol on Windows)
log_file = os.path.join(os.path.dirname(__file__), "server.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file)]
)
logger = logging.getLogger("job-search-server")
logger.info("=" * 60)
logger.info("MCP Server started")
logger.info("=" * 60)

# ===== SIMPLE CACHE =====
cache = {}

def get_cache_key(query: str, location: str) -> str:      #Combines query + location into one string
                                                           #Example: "AI Engineer:Bangalore"
                                                        #Converts "AI Engineer:Bangalore" into a hash (like a fingerprint)
                                                     #Example: "a1b2c3d4e5f6..." (long unique code)'''
    key_string = f"{query}:{location}"
    return hashlib.md5(key_string.encode()).hexdigest()

def is_cache_valid(timestamp: datetime) -> bool:
    return datetime.now() - timestamp < timedelta(hours=CACHE_DURATION_HOURS)

def get_from_cache(query: str, location: str):
    key = get_cache_key(query, location)
    if key in cache:
        cached_data, timestamp = cache[key]
        if is_cache_valid(timestamp):
            logger.info(f"✓ Cache hit for: {query} in {location}")
            return cached_data
        else:
            del cache[key]
            logger.info(f"✗ Cache expired for: {query} in {location}")
    return None

def save_to_cache(query: str, location: str, result: dict):
    key = get_cache_key(query, location)
    cache[key] = (result, datetime.now())
    logger.info(f"📦 Cached result for: {query} in {location}")

server = Server("job-search-server")

def format_job_response(jobs_data: dict) -> dict:
    """Convert API response to structured JSON format"""
    try:
        jobs = jobs_data.get("data", [])
        logger.info(f"Formatting {len(jobs)} jobs from API response")
        
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
            for job in jobs[:MAX_JOBS_RETURN]
        ]
        
        result = {
            "success": True,
            "count": len(formatted_jobs),
            "jobs": formatted_jobs
        }
        logger.info(f"✓ Successfully formatted {len(formatted_jobs)} jobs")
        return result
        
    except Exception as e:
        logger.error(f"✗ Error formatting response: {str(e)}")
        return {"success": False, "error": str(e), "jobs": []}

'''def format_job_response(jobs_data: dict) -> dict:
    """Convert API response to structured JSON format"""
    try:
        jobs = jobs_data.get("data", [])
        return {
            "success": True,
            "count": len(jobs),
            "jobs": [
                {
                    "title": job.get("job_title", "N/A"),
                    "company": job.get("employer_name", "N/A"),
                    "location": f"{job.get('job_city', 'N/A')}, {job.get('job_country', '')}",
                    "type": job.get("job_employment_type", "N/A"),
                    "posted": job.get("job_posted_at_datetime_utc", "N/A"),
                    "apply_link": job.get("job_apply_link", "N/A"),
                    "description_snippet": (job.get("job_description", "") or "")[:200] + "..."
                }
                for job in jobs[:10]
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e), "jobs": []}'''

FALLBACK_RESPONSE = {
    "success": False,
    "error": "Job search temporarily unavailable. Please try again later.",
    "jobs": []
}

@server.list_tools()
async def handle_list_tools():
    """List available tools"""
    logger.info("Agent asking: What tools are available?")
    return [
        types.Tool(
            name="search_jobs",
            description="Search for job listings",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Job title or keywords"
                    },
                    "location": {
                        "type": "string",
                        "description": "City or country"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle tool calls from the ADK agent"""
    if name == "search_jobs":
        logger.info(f"Agent calling tool: {name} with arguments: {arguments}")
        logger.info(f"🔄 [START] search_jsearch call")
        result = await search_jsearch(
            arguments.get("query", ""),
            arguments.get("location", "")
        )
        logger.info(f"🔄 [END] search_jsearch call, got result")
        logger.info(f"🔄 Preparing response for MCP...")
        response = [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        logger.info(f"🔄 Returning response to agent...")
        return response
    logger.error(f"✗ Unknown tool requested: {name}")
    raise ValueError(f"Unknown tool: {name}")

async def search_jsearch(query: str, location: str) -> dict:
    """Search jobs using JSearch API with timeout"""

    logger.info(f"🔍 SEARCH START: query='{query}', location='{location}'")

    # Check cache
    cached_result = get_from_cache(query, location)
    if cached_result:
        logger.info(f"✅ CACHE HIT - returning cached results")
        return cached_result

    # Get API key
    api_key = os.getenv("RAPIDAPI_KEY")
    logger.info(f"🔑 API Key check: {'present' if api_key else 'MISSING'}")

    if not api_key or api_key == "your_rapidapi_key_here":
        logger.error("✗ API key not configured or is placeholder")
        return {
            "success": False,
            "error": "API key not configured. Please set RAPIDAPI_KEY in .env file.",
            "jobs": []
        }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    # Build query with proper format
    logger.info(f"📝 Building search query from: query='{query}', location='{location}'")

    if location:
        if "india" not in location.lower():
            search_query = f"{query} jobs in {location} India"
        else:
            search_query = f"{query} jobs in {location}"
    else:
        search_query = f"{query} jobs"

    logger.info(f"📝 Final search query: '{search_query}'")

    params = {"query": search_query, "num_pages": 1}
    logger.info(f"📝 API params: {params}")

    try:
        logger.info(f"📡 Calling {API_ENDPOINT}")
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            logger.info(f"📡 Request headers: {list(headers.keys())}")
            response = await client.get(API_ENDPOINT, headers=headers, params=params)
            logger.info(f"📡 Response status: {response.status_code}")
            response.raise_for_status()

            logger.info(f"🔄 Parsing JSON response...")
            data = response.json()
            logger.info(f"🔄 JSON parsed successfully")
            logger.info(f"📡 API response keys: {list(data.keys())}")
            logger.info(f"📡 Raw response data count: {len(data.get('data', []))}")

            logger.info(f"🔄 Formatting response...")
            result = format_job_response(data)
            logger.info(f"🔄 Formatting complete")
            logger.info(f"✅ Formatted result: {result.get('count', 0)} jobs found")

            # Save to cache
            logger.info(f"🔄 Saving to cache...")
            save_to_cache(query, location, result)
            logger.info(f"🔄 Cache save complete")
            logger.info(f"✅ SEARCH COMPLETE: {result.get('count', 0)} jobs")
            return result

    except httpx.TimeoutException:
        logger.error(f"✗ API timeout after {API_TIMEOUT} seconds")
        return {
            "success": False,
            "error": "Request timed out. Please try again.",
            "jobs": []
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"✗ API HTTP error: {e.response.status_code}")
        logger.error(f"✗ Response text: {e.response.text[:500]}")
        return {
            "success": False,
            "error": f"API error: {e.response.status_code}",
            "jobs": []
        }
    except Exception as e:
        logger.error(f"✗ Unexpected error: {str(e)}")
        logger.error(f"✗ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"✗ Traceback: {traceback.format_exc()}")
        return FALLBACK_RESPONSE

async def main():
    """Start the MCP server using stdio transport"""
    logger.info("🚀 Starting MCP Job Search Server...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="job-search",
                server_version="1.0.0",
                capabilities={}
            )
        )
    logger.info("🛑 Server stopped")     

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
