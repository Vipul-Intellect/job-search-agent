# 🔍 Job Search Agent - AI-Powered Job Discovery

**An intelligent AI agent that searches for jobs using Google ADK, MCP, and Gemini AI**

[![GitHub](https://img.shields.io/badge/GitHub-View%20Repo-blue)](https://github.com/Vipul-Intellect/job-search-agent)
[![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Live%20Demo-green)](https://job-search-agent-179840969159.me-central1.run.app)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📖 What is This?

This is an **AI Job Intelligence Agent** that:
1. **Takes your job search query** (e.g., "ML Engineer in Bangalore")
2. **Uses Google ADK** to create an intelligent agent
3. **Connects via MCP** to RapidAPI's JSearch
4. **Returns real job listings** with apply links
5. **All deployed on Cloud Run** (live & accessible)

---

## 🎯 Key Features

### Core Features
- ✅ **AI-Powered Search** - Uses Gemini 2.5 Flash LLM
- ✅ **MCP Integration** - Secure tool-based API access
- ✅ **Real Data** - Jobs from RapidAPI JSearch (Uber, Barclays, Boeing, etc.)
- ✅ **Beautiful UI** - Professional Bootstrap 5 interface
- ✅ **Structured Response** - JSON with all job details

### Advanced Features (Phase 2)
- ✅ **Pagination** - Browse jobs across 3 pages (10 per page)
- ✅ **Level Filtering** - Filter by job level (Entry, Mid, Senior, C-Level, Internship)
- ✅ **Smart Caching** - 1-hour cache per search combo
- ✅ **Rate Limiting** - 10 requests/IP/minute (prevents abuse)
- ✅ **Input Validation** - Blocks injection attacks & malicious input

---

## 🏗️ How It Works (Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (Browser/CLI)                       │
│                  Searches: "ML Engineer"                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP POST /search
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FLASK API (main.py)                       │
│  • Input Validation                                         │
│  • Rate Limiting                                            │
│  • Response Formatting                                      │
└────────────────────────┬────────────────────────────────────┘
                         │ Calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              ADK LlmAgent + InMemoryRunner                   │
│  • Gemini 2.5 Flash Model                                  │
│  • Instruction: "Call search_jobs tool"                    │
│  • Receives: {query, location, page, level}               │
└────────────────────────┬────────────────────────────────────┘
                         │ Agent decides: "I need search_jobs"
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          MCP Tool: search_jobs (McpToolset)                 │
│  Tool Schema:                                               │
│  - query (required)                                         │
│  - location (required)                                      │
│  - page (1-3, optional)                                    │
│  - level (entry/mid/senior/all, optional)                 │
└────────────────────────┬────────────────────────────────────┘
                         │ Spawns subprocess
                         ▼
┌─────────────────────────────────────────────────────────────┐
│        MCP Server (mcp_job_server/server.py)               │
│  • Receives: search_jobs call with parameters              │
│  • Validates pagination & level                            │
│  • Applies caching logic                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ If not cached
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              RapidAPI JSearch Endpoint                      │
│  • Real job listings database                              │
│  • Returns: ~30 jobs (with 3 pages)                        │
│  • Fields: title, company, location, link, etc.            │
└────────────────────────┬────────────────────────────────────┘
                         │ Response flows back
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           MCP Server Processing                             │
│  • Formats jobs into structured JSON                        │
│  • Filters by level if requested                           │
│  • Paginates (10 per page)                                 │
│  • Caches result for 1 hour                                │
└────────────────────────┬────────────────────────────────────┘
                         │ Result returned
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              ADK Agent Receives Result                      │
│  • Extracts job data from tool response                     │
│  • Formats for user consumption                             │
└────────────────────────┬────────────────────────────────────┘
                         │ Returns to Flask
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Flask API Returns JSON Response                  │
│  {                                                          │
│    "success": true,                                         │
│    "jobs": [10 job objects],                               │
│    "page": 1,                                               │
│    "total_pages": 3,                                        │
│    "level_filter": "all"                                    │
│  }                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP 200
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              USER Gets Results                              │
│  • Beautifully formatted job cards                          │
│  • "View Job" link (external apply)                        │
│  • "Copy Link" button                                       │
│  • Pagination buttons (if multiple pages)                   │
│  • Level filter dropdown                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1️⃣ Prerequisites
```bash
Python 3.11+
Google AI API Key (free from https://aistudio.google.com/app/apikey)
RapidAPI Key (free from https://rapidapi.com/letscrape-6baByCGuQzVgP0v3/api/jsearch)
```

### 2️⃣ Setup
```bash
cd job-search-agent
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 3️⃣ Configure Keys
```bash
cp .env.example .env
# Edit .env and add your keys
```

### 4️⃣ Run Locally
```bash
# Terminal 1: Start MCP Server
python mcp_job_server/server.py

# Terminal 2: Start Flask API
python main.py
# Visit: http://localhost:5000
```

### 5️⃣ Or Use Live Cloud Run
```
https://job-search-agent-179840969159.me-central1.run.app
```

---

## 📊 Features in Detail

### Feature 1: Basic Job Search
**Request:**
```bash
curl -X POST https://job-search-agent-xxx.run.app/search \
  -H "Content-Type: application/json" \
  -d '{"query":"ML Engineer","location":"Bangalore"}'
```

**Response:**
```json
{
  "success": true,
  "job_count": 10,
  "jobs": [
    {
      "title": "Senior ML Engineer",
      "company": "Uber",
      "location": "Bengaluru, IN",
      "type": "Full-time",
      "posted": "2026-03-04",
      "apply_link": "https://www.uber.com/...",
      "level": "senior_level"
    }
    // ... 9 more jobs
  ]
}
```

### Feature 2: Pagination (3 Pages)
**Request:**
```bash
curl -X POST https://job-search-agent-xxx.run.app/search \
  -d '{"query":"ML Engineer","location":"Bangalore","page":2}'
```

**What Happens:**
- Page 1: Jobs 1-10
- Page 2: Jobs 11-20
- Page 3: Jobs 21-30

**Response includes:**
```json
{
  "page": 2,
  "total_pages": 3,
  "total_available": 28
}
```

### Feature 3: Level Filtering
**Request:**
```bash
curl -X POST https://job-search-agent-xxx.run.app/search \
  -d '{
    "query":"ML Engineer",
    "location":"Bangalore",
    "level":"senior_level"
  }'
```

**Available Levels:**
- `all` - All job levels
- `entry_level` - Intern, Graduate roles
- `mid_level` - 3-7 years experience
- `senior_level` - 7+ years experience
- `c-level` - Leadership positions
- `internship` - Internship programs

**UI Dropdown:**
```
┌─ All Levels
├─ Entry Level (Intern, Graduate)
├─ Mid Level (3-7 years)
├─ Senior Level (7+ years)
├─ C-Level / Leadership
└─ Internship
```

### Feature 4: Combined Pagination + Filtering
**Request:**
```bash
curl -X POST https://job-search-agent-xxx.run.app/search \
  -d '{
    "query":"Data Scientist",
    "location":"New York",
    "page": 2,
    "level": "mid_level"
  }'
```

Returns: Page 2 of mid-level Data Scientist jobs in New York

---

## 🎓 Academy Requirements Met

| Requirement | Status | How |
|-------------|--------|-----|
| **Implemented using ADK** | ✅ | LlmAgent from google.adk.agents |
| **Uses MCP to connect to tool** | ✅ | McpToolset with search_jobs tool |
| **Retrieves structured data** | ✅ | Real data from RapidAPI JSearch |
| **Uses data in response** | ✅ | Jobs returned in JSON response |
| **Cloud Run Deployment** | ✅ | Live at cloud-run URL |

---

## 🔒 Security Features

### Input Validation
- ✅ Query length: Max 500 characters
- ✅ Location length: Max 200 characters
- ✅ Injection prevention: Blocks SQL/bash/python keywords
- ✅ Pattern matching: Only alphanumeric + safe characters

### Rate Limiting
- ✅ 10 requests per IP per 60 seconds
- ✅ Returns `429 Too Many Requests` if exceeded

### Error Handling
- ✅ No sensitive data in error messages
- ✅ All errors return proper HTTP status codes
- ✅ Graceful fallback if agent fails

### API Key Security
- ✅ Keys stored in environment variables
- ✅ Never exposed in code
- ✅ Never logged in responses

---

## 💾 Caching Strategy

**Cache Key:** `MD5(query + location + page + level)`

**Duration:** 1 hour per cached result

**Example:**
```
First search: "ML Engineer" in "Bangalore" (page 1, all levels)
  → Calls RapidAPI, caches result
Second identical search within 1 hour
  → Returns cached result instantly (<100ms)
Same query but different page
  → Uses cached full results, paginates locally
```

---

## 📁 File Structure

```
job-search-agent/
├── main.py                          # Flask API + ADK Agent orchestration
├── mcp_job_server/
│   └── server.py                   # MCP Server (tool implementation)
├── job_agent/
│   └── agent.py                    # ADK LlmAgent configuration
├── templates/
│   └── index.html                  # Web UI (Bootstrap 5)
├── requirements.txt                # Python dependencies
├── Dockerfile                       # Cloud Run deployment
├── .env.example                     # Example environment variables
└── README.md                        # This file
```

---

## 🐳 Deploy to Cloud Run

### 1. Ensure Files Exist
```bash
# Check critical files
ls main.py mcp_job_server/server.py job_agent/agent.py templates/index.html
```

### 2. Set Environment Variables in Cloud Run
```bash
gcloud run deploy job-search-agent \
  --source . \
  --region me-central1 \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY,RAPIDAPI_KEY=$RAPIDAPI_KEY \
  --allow-unauthenticated
```

### 3. Access Live
```
https://job-search-agent-179840969159.me-central1.run.app
```

---

## 🧪 Testing

### Test Health Endpoint
```bash
curl https://job-search-agent-xxx.run.app/health
# Response: {"healthy": true, "ready": true}
```

### Test Basic Search
```bash
curl -X POST https://job-search-agent-xxx.run.app/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Python Developer","location":"Remote"}'
```

### Test with Pagination
```bash
curl -X POST https://job-search-agent-xxx.run.app/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Data Science","location":"San Francisco","page":2}'
```

### Test with Filtering
```bash
curl -X POST https://job-search-agent-xxx.run.app/search \
  -H "Content-Type: application/json" \
  -d '{"query":"DevOps Engineer","location":"AWS","level":"senior_level"}'
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| First Search Response | 2-3 seconds |
| Cached Response | <100ms |
| Concurrent Users | Auto-scales (Cloud Run) |
| Max Jobs Per Query | 30 (3 pages × 10 jobs) |
| Cache Duration | 1 hour |

---

## 🚨 Important Notes

### RapidAPI Free Tier
- **Limit:** 100 requests/month
- **Cost:** Free
- **After limit:** Returns error (no additional charges)

### Gemini API Free Tier
- **Limit:** 60 requests/minute
- **Cost:** Free for testing, ~$0.00005 per request in production

### Cloud Run Pricing
- **Free tier:** 2M requests/month
- **After:** $0.40 per 1M requests
- **Monthly estimate for Academy:** <$0.10

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📝 License

MIT License - Feel free to use, modify, and distribute

---

## 👨‍💻 Author

**Vipul Gupta**
- GitHub: [@Vipul-Intellect](https://github.com/Vipul-Intellect)
- Project: Job Search Agent using Google ADK + MCP + Gemini

---

## 🙋 Support

For issues or questions:
1. Check existing GitHub issues
2. Review the code comments (well-documented)
3. Test with the Cloud Run URL
4. Check logs at: Cloud Run Console

---

## ✨ What's Special About This Project?

1. **Real AI Agent** - Not a mock, actual ADK LlmAgent execution
2. **Tool Integration** - MCP tools actually invoked by agent
3. **Real Data** - Jobs from real API (not dummy data)
4. **Production Ready** - Deployed on Cloud Run, live now
5. **Well Architected** - Proper separation of concerns
6. **Fully Featured** - Search, pagination, filtering, caching
7. **Secure** - Validation, rate limiting, error handling
8. **Beautiful UI** - Professional design with Bootstrap

---

**Ready to find your next job? Click the Cloud Run link above!** 🚀
