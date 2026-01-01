# 重启Web服务器脚本
# 用于修改代码后快速重启Flask应用

Write-Host "正在停止现有的Flask进程..." -ForegroundColor Yellow

# 查找并停止占用5001端口的进程
$connections = Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue
if ($connections) {
    $processes = $connections | ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
    $processes | Where-Object { $_.ProcessName -like "*python*" } | Stop-Process -Force
    Write-Host "已停止 $($processes.Count) 个进程" -ForegroundColor Green
    Start-Sleep -Seconds 1
} else {
    Write-Host "未发现运行中的Flask进程" -ForegroundColor Cyan
}

# 清理Python缓存
Write-Host "清理Python缓存..." -ForegroundColor Yellow
Get-ChildItem -Path "web\__pycache__" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path "src\**\__pycache__" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "缓存已清理" -ForegroundColor Green

# 启动Flask
Write-Host "`n正在启动Flask服务器..." -ForegroundColor Yellow
Write-Host "访问地址: http://127.0.0.1:5001" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务器`n" -ForegroundColor Gray

$env:PYTHONDONTWRITEBYTECODE = 1
py web/app.py

