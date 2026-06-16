@echo off
chcp 65001 >nul
title 东华倪家 - 家庭门户
cd /d "%~dp0"

echo.
echo ===============================================
echo        东华倪家 - 家庭门户网站
echo ===============================================
echo.

REM 检查 .ngrok_token 文件是否存在
if exist ".ngrok_token" (
    echo [√] 已检测到 ngrok 配置，启动公网隧道...
) else (
    echo [提示] 未检测到 ngrok 配置
    echo.
    echo 想让外网也能访问？按以下步骤操作：
    echo   1. 打开浏览器访问 https://ngrok.com 注册免费账号
    echo   2. 登录后访问 https://dashboard.ngrok.com/get-started/your-authtoken
    echo   3. 复制你的 token，粘贴到下方并回车
    echo   4. 或者：直接在当前目录创建 .ngrok_token 文件，粘贴 token 进去
    echo.
    set /p TOKEN="请输入你的 ngrok token (跳过请直接回车): "
    if not "!TOKEN!"=="" (
        echo !TOKEN!>.ngrok_token
        echo [√] Token 已保存！下次启动自动连接
    )
)

echo.
echo 正在启动服务器...
echo.

python server.py %*

pause
