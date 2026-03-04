# MT5 Bridge Startup Script (Windows VPS)
# Run this on the Windows VPS with MT5 terminal open

$env:MT5_BRIDGE_SECRET = "your-bridge-secret-here"
$env:MT5_LOGIN = ""          # Optional: MT5 account login
$env:MT5_PASSWORD = ""       # Optional: MT5 account password
$env:MT5_SERVER = ""         # Optional: MT5 server name

Write-Host "Starting MT5 Bridge on port 9000..."
uvicorn app:app --host 0.0.0.0 --port 9000 --workers 1
