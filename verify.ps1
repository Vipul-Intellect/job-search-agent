# JOB SEARCH AGENT - READINESS CHECK
Write-Host "=====================================" -ForegroundColor Magenta
Write-Host "JOB SEARCH AGENT - READINESS CHECK" -ForegroundColor Magenta
Write-Host "=====================================" -ForegroundColor Magenta

$allPass = $true

# Check 1: Files exist
Write-Host "`n[1/5] Checking files..." -ForegroundColor Cyan
$files = @(
    "job_agent\agent.py",
    "job_agent\__init__.py",
    "mcp_job_server\server.py",
    "requirements.txt",
    ".env"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  OK $file"
    } else {
        Write-Host "  FAIL $file MISSING"
        $allPass = $false
    }
}

# Check 2: API Keys
Write-Host "`n[2/5] Checking API keys..." -ForegroundColor Cyan
$envContent = Get-Content .env -Raw
if ($envContent -match "GOOGLE_API_KEY=AIza") {
    Write-Host "  OK GOOGLE_API_KEY present"
} else {
    Write-Host "  FAIL GOOGLE_API_KEY missing"
    $allPass = $false
}

if ($envContent -match "RAPIDAPI_KEY=") {
    Write-Host "  OK RAPIDAPI_KEY present"
} else {
    Write-Host "  FAIL RAPIDAPI_KEY missing"
    $allPass = $false
}

# Check 3: Dependencies
Write-Host "`n[3/5] Checking requirements.txt..." -ForegroundColor Cyan
$reqContent = Get-Content requirements.txt -Raw
$deps = @("google-adk", "google-generativeai", "mcp", "httpx", "python-dotenv")
foreach ($dep in $deps) {
    if ($reqContent -match $dep) {
        Write-Host "  OK $dep"
    } else {
        Write-Host "  FAIL $dep missing"
        $allPass = $false
    }
}

# Check 4: Model version
Write-Host "`n[4/5] Checking Gemini model..." -ForegroundColor Cyan
$agentContent = Get-Content job_agent\agent.py -Raw
if ($agentContent -match "gemini-2.5-flash") {
    Write-Host "  OK Using gemini-2.5-flash"
} else {
    Write-Host "  FAIL Wrong model"
    $allPass = $false
}

# Check 5: MCP Connection
Write-Host "`n[5/5] Checking MCP tools..." -ForegroundColor Cyan
if ($agentContent -match "mcp_tools") {
    Write-Host "  OK MCP tools connected"
} else {
    Write-Host "  FAIL MCP tools NOT connected"
    $allPass = $false
}

# Final result
Write-Host "`n=====================================" -ForegroundColor Magenta
if ($allPass) {
    Write-Host "ALL CHECKS PASSED - Ready for adk run" -ForegroundColor Green
} else {
    Write-Host "SOME CHECKS FAILED - Fix before running" -ForegroundColor Red
}
Write-Host "=====================================" -ForegroundColor Magenta
