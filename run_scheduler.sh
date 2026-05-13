#!/bin/bash
# PD科学 — 每日爬虫调度器启动脚本
#
# 用法:
#   ./run_scheduler.sh          # 前台运行
#   ./run_scheduler.sh &        # 后台运行
#   ./run_scheduler.sh stop     # 停止后台运行的调度器

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
PID_FILE="$PROJECT_DIR/.scheduler.pid"

stop_scheduler() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "停止调度器 (PID: $PID)..."
            kill "$PID"
            rm -f "$PID_FILE"
            echo "已停止。"
        else
            echo "调度器未在运行（PID 文件存在但进程已不存在）。"
            rm -f "$PID_FILE"
        fi
    else
        echo "未找到运行中的调度器。"
    fi
}

case "${1:-start}" in
    stop)
        stop_scheduler
        exit 0
        ;;
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "调度器正在运行 (PID: $PID)"
            else
                echo "调度器未运行（PID 文件残留）。"
            fi
        else
            echo "调度器未运行。"
        fi
        exit 0
        ;;
    start|*)
        # 检查是否已运行
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "调度器已在运行中 (PID: $PID)"
                exit 0
            fi
        fi

        echo "启动 PD科学 每日爬虫调度器..."
        cd "$PROJECT_DIR"
        nohup "$VENV_PYTHON" "$PROJECT_DIR/src/scheduler.py" > /dev/null 2>&1 &
        echo $! > "$PID_FILE"
        echo "调度器已启动 (PID: $!)"
        echo "日志文件: $PROJECT_DIR/logs/scheduler.log"
        ;;
esac
