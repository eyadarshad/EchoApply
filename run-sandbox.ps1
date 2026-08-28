# run-sandbox.ps1 - Claude Code Secure Sandbox Launcher
# Requires Docker Desktop running on Windows

# 1. Ask for Aerolink API Key if not already set as env variable
if (-not $env:AEROLINK_API_KEY) {
    $apiKey = Read-Host -Prompt "Enter your Aerolink API Key (e.g. sk-...)"
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        Write-Error "Error: API Key is required."
        exit 1
    }
} else {
    $apiKey = $env:AEROLINK_API_KEY
}

# 2. Get current directory path (Windows format to POSIX format for Docker mounting)
$currentDir = Get-Location
Write-Host "[*] Setting up sandbox for workspace: $currentDir"

# 3. Resolve scratch path where Dockerfile and entrypoint are stored
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = "." }

# 4. Copy current directory context files to build context if needed
# (Docker requires the files to be in the same folder during build)
# We will execute the docker build directly inside the scratch folder
Write-Host "[*] Building security Docker image (this may take a minute on first run)..."
Push-Location $scriptDir
docker build -f Dockerfile.sandbox -t claudecode-sandbox .
Pop-Location

# 5. Launch the Sandbox
Write-Host "[+] Launching Claude Code Sandbox with Outbound Traffic Locking..."
Write-Host "[+] Injected Base URL: https://api.aerolink.lat/v1"
Write-Host "[+] NET_ADMIN capabilities enabled to configure container firewall."

docker run -it --rm `
  --cap-add=NET_ADMIN `
  -v "${currentDir}:/workspace" `
  -e "ANTHROPIC_BASE_URL=https://api.aerolink.lat/v1" `
  -e "ANTHROPIC_API_KEY=$apiKey" `
  claudecode-sandbox `
  claude

Write-Host "[+] Sandbox terminated."
