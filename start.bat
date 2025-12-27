@echo off
echo Starting MendyGo System...

:: Kill existing processes if any
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1

:: Start Python Bridge in the background
echo Starting [1/3] Python Bridge (AI Logic)...
start "MendyGo - Python Bridge" cmd /k ".\mendy\Scripts\python.exe server\api_bridge.py"

:: Start Node Server in the background
echo Starting [2/3] Node Server (Proxy)...
cd server
start "MendyGo - Node Proxy" cmd /k "npm run dev"
cd ..

:: Start Frontend
echo Starting [3/3] Frontend (Dashboard UI)...
cd client
start "MendyGo - Dashboard UI" cmd /k "npm run dev"

echo System started. Please check the windows for logs.
