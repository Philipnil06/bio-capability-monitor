$ErrorActionPreference = "Stop"

$py = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
if (-not (Test-Path $py)) {
    throw "Python not found at $py"
}

$lan = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Sort-Object -Property SkipAsSource, InterfaceMetric |
    Select-Object -First 1 -ExpandProperty IPAddress
)

if (-not $lan) {
    throw "Could not detect LAN IPv4 address."
}

Write-Host "Starting Streamlit on LAN..."
Write-Host "Local URL:   http://127.0.0.1:8501"
Write-Host "Network URL: http://$lan`:8501"
Write-Host ""
Write-Host "Keep this terminal open while using the UI."

& $py -m streamlit run src/debug_ui.py `
    --server.address 0.0.0.0 `
    --server.port 8501 `
    --server.headless true `
    --browser.gatherUsageStats false
