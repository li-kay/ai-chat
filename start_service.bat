@echo off
chcp 65001 > nul
echo 正在启动美团客服后端服务...
echo 服务启动后请访问: http://localhost:5050
start http://localhost:5050
python websocket_server.py
pause
