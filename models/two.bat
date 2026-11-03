@echo off
set "LLAMA=C:\ПУТЬ\llama-b10679-bin-win-cpu-x64"
set "MCP=C:\models\mcp.json"
cd /d "%LLAMA%" || (echo no llama folder & pause & exit /b)
taskkill /F /IM llama-server.exe >nul 2>&1
timeout /t 2 >nul

echo === 1) Qwen3-1.7B  +  INTERNET  ->  http://127.0.0.1:8080 ===
start "Qwen3-search" llama-server.exe -m C:\models\МОДЕЛЬ.gguf --jinja --agent --mcp-servers-config "%MCP%" --ui-mcp-proxy --host 127.0.0.1 --port 8080 -t 2 -c 4096 --cache-type-k q4_0 --cache-type-v q4_0

timeout /t 3 >nul
echo === 2) Qwen2.5-3B  +  INTERNET  ->  http://127.0.0.1:8081 ===
start "Qwen25-search" llama-server.exe -m C:\models\МОДЕЛЬ.gguf --jinja --agent --mcp-servers-config "%MCP%" --ui-mcp-proxy --host 127.0.0.1 --port 8081 -t 2 -c 2048 --cache-type-k q4_0 --cache-type-v q4_0

echo.
echo Both launched WITH search. Watch Task Manager: 95%%+ mem + disk = swap, close one.
pause
