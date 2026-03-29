# AI Job Intelligence Agent

An AI-powered job search agent built with Google ADK, MCP, and Gemini that intelligently searches job listings using RapidAPI's JSearch.

## 🎯 Features

✅ **AI-Powered Search** - Uses Gemini 2.5 Flash for intelligent responses  
✅ **MCP Integration** - Model Context Protocol for secure external API access  
✅ **Structured Results** - Returns well-formatted job data with all details  
✅ **Smart Caching** - 1-hour cache to reduce API calls  
✅ **Error Handling** - Graceful fallbacks and detailed logging  
✅ **Production-Ready** - Cloud Run deployment ready  

## 📋 Requirements

- Python 3.11+
- Google AI Gemini API key (free)
- RapidAPI JSearch API key (free tier available)
- Virtual environment recommended

## 🚀 Quick Start

### 1. Setup

```bash
# Clone or navigate to project
cd job-search-agent

# Create virtual environment
python -m venv venv

# Activate venv
source venv/bin/activate    # Linux/Mac
# OR
venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and add your keys:
```
GOOGLE_API_KEY=your_key_from_https://aistudio.google.com/app/apikey
RAPIDAPI_KEY=your_key_from_https://rapidapi.com/letscrape-6beBT/api/jsearch
```

### 3. Run Locally

```bash
adk run
```

Then ask questions like:
- "Find AI Engineer jobs in Bangalore"
- "Show me Python Developer jobs in India"
- "Search for product manager roles in San Francisco"

## 🏗️ Architecture

```
User Input
    ↓
ADK Agent (Gemini 2.5 Flash)
    ↓
MCP Toolset (search_jobs)
    ↓
RapidAPI JSearch
    ↓
Formatted Job Results
    ↓
Agent Response
```

## 📁 Project Structure

```
job-search-agent/
├── job_agent/
│   ├── __init__.py
│   └── agent.py              # ADK Agent with MCP tools
├── mcp_job_server/
│   ├── __init__.py
│   └── server.py             # MCP Server for job search
├── requirements.txt          # Python dependencies
├── .env                      # Your API keys (git ignored)
├── .env.example              # Template for API keys
├── .gitignore                # Git ignore rules
├── Dockerfile                # Cloud Run deployment
└── README.md                 # This file
```

## 🔧 How It Works

1. **User Query** → "Find AI Engineer jobs in Bangalore"
2. **ADK Agent** → Receives query and decides to use search_jobs tool
3. **MCP Server** → Handles tool requests and formats parameters
4. **RapidAPI** → Calls JSearch API with authenticated headers
5. **Caching** → Stores results for 1 hour to reduce API calls
6. **Response** → Agent formats results with Gemini and returns to user

## 📊 Response Format

```json
{
  "success": true,
  "count": 5,
  "jobs": [
    {
      "title": "Senior AI Engineer",
      "company": "TechCorp",
      "location": "Bangalore, India",
      "type": "Full-time",
      "posted": "2026-03-29",
      "apply_link": "https://...",
      "description_snippet": "We are looking for..."
    }
  ]
}
```

## 🌥️ Deploy to Cloud Run (Phase 5)

```bash
# Build Docker image
docker build -t job-search-agent .

# Deploy to Cloud Run (requires GCP project)
gcloud run deploy job-search-agent \
  --image job-search-agent \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY,RAPIDAPI_KEY=$RAPIDAPI_KEY \
  --memory 512Mi \
  --timeout 300
```

## 🔑 Getting API Keys

### Google Gemini API Key
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy and save in `.env`

### RapidAPI JSearch Key
1. Go to https://rapidapi.com/letscrape-6beBT/api/jsearch
2. Subscribe (free tier available)
3. Copy API key from Dashboard
4. Save in `.env`

## 🧪 Testing

```bash
# Test locally
adk run

# Example queries to test:
# - "Find jobs in London"
# - "Show AI jobs in USA"
# - "Search for React Developer positions in Canada"
```

## 📚 Technology Stack

- **ADK** - Google Agent Development Kit
- **Gemini** - Google's AI model
- **MCP** - Model Context Protocol
- **RapidAPI** - Third-party API marketplace
- **httpx** - Async HTTP client
- **python-dotenv** - Environment variable management

## 🐛 Troubleshooting

### "API key not valid"
- Verify key in `.env`
- Check key is from correct source (Gemini API, not Vertex AI)

### "MCP server connection failed"
- Ensure `mcp_job_server/server.py` exists
- Check Python path in agent.py

### "No jobs found"
- Try broader search terms
- Check RapidAPI key is valid

### "Rate limit exceeded"
- Wait a few minutes (free tier quota resets hourly)
- Upgrade API plan for higher limits

## 📝 Notes

- Free tier quotas reset hourly for RapidAPI
- Gemini API has daily free tier limits (~1M tokens)
- Job results are cached for 1 hour
- Cloud Run needs environment variables configured

## 🎓 Academy Submission

This project meets GenAI APAC Academy requirements:
✅ Uses ADK (LlmAgent)
✅ Uses MCP (MCPToolset)
✅ Retrieves external data (RapidAPI)
✅ Uses structured responses (JSON)
✅ Production deployment ready (Cloud Run)
✅ Complete documentation

## 📄 License

This is an educational project for GenAI APAC Academy.

---

**Build Status:** ✅ Ready for local testing and Cloud Run deployment
