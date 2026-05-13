#!/usr/bin/env python3
"""
每日文献爬取调度器。
在后台持续运行，每天 08:00 自动执行一次 crawler_agent.run_agent()。

用法:
    python src/scheduler.py           # 前台运行
    nohup python src/scheduler.py &   # 后台运行
    ./run_scheduler.sh                # 推荐方式
"""

import sys
import os
import time
import logging
from datetime import datetime

# 确保项目根目录在 path 中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(project_root, "logs", "scheduler.log"),
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger(__name__)

# 确保 logs 目录存在
os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)


def run_daily_job():
    """执行每日爬取任务。"""
    logger.info("========== 开始每日文献爬取 ==========")
    try:
        from crawler_agent import run_agent
        run_agent()
        logger.info("========== 每日文献爬取完成 ==========")
    except Exception as e:
        logger.error(f"爬取出错: {e}", exc_info=True)
        logger.info("========== 任务异常终止 ==========")


def main():
    logger.info("调度器启动，每天 08:00 执行一次爬取")

    import schedule
    schedule.every().day.at("08:00").do(run_daily_job)

    # 首次启动时，检查今天是否已经执行过
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_dir = os.path.join(project_root, "reference", "daily")
    today_file = os.path.join(daily_dir, f"{today_str}.json")
    if not os.path.exists(today_file):
        logger.info("今日尚未爬取，立即执行首次任务...")
        run_daily_job()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
