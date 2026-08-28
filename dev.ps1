# SmartApply AI - Unified Development Runner (Windows PowerShell)
# Launches both FastAPI Backend (with auto-reload) and Next.js Frontend (with Hot-Module-Replacement)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🚀 Starting SmartApply AI Full-Stack Development Environment" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$RootPath = $PSScriptRoot
$VenvPython = Join-Path $RootPath ".venv\Scripts\python.exe"
$FrontendDir = Join-Path $RootPath "frontend"

if (-not (Test-Path $VenvPython)) {
    Write-Host "⚠️  Virtual environment not found at $VenvPython. Using system python..." -ForegroundColor Yellow
    $VenvPython = "python"
}

# Check if concurrently is available via npx
$ConcurrentlyAvailable = $false
try {
    $testNpx = Start-Process -FilePath "npx" -ArgumentList "-y concurrently --version" -NoNewWindow -PassThru -Wait -ErrorAction SilentlyContinue
    if ($testNpx.ExitCode -eq 0) {
        $ConcurrentlyAvailable = $true
    }
} catch {
    $ConcurrentlyAvailable = $false
}

if ($ConcurrentlyAvailable) {
    Write-Host "⚡ Using concurrently for unified colorized logging..." -ForegroundColor Green
    $backendCmd = "`"$VenvPython`" -m uvicorn app.main:app --reload --port 8000 --app-dir backend"
    $frontendCmd = "npm run dev --prefix frontend"
    
    npx -y concurrently `
        --kill-others `
        --prefix "[{name}]" `
        --names "backend,frontend" `
        --prefix-colors "blue.bold,magenta.bold" `
        "$backendCmd" `
        "$frontendCmd"
} else {
    Write-Host "Starting Backend on http://127.0.0.1:8000 (auto-reloading)..." -ForegroundColor Cyan
    $backendProcess = Start-Process -FilePath $VenvPython -ArgumentList "-m uvicorn app.main:app --reload --port 8000 --app-dir backend" -PassThru -NoNewWindow

    Write-Host "Starting Frontend on http://localhost:3000 (Fast Refresh)..." -ForegroundColor Magenta
    Set-Location $FrontendDir
    $frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" -PassThru -NoNewWindow

    Write-Host "✅ Both servers are running! Press Ctrl+C in this terminal to stop both." -ForegroundColor Green

    try {
        Wait-Process -Id $backendProcess.Id, $frontendProcess.Id
    } finally {
        Write-Host "Stopping servers..." -ForegroundColor Yellow
        Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
        Stop-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue
    }
}
