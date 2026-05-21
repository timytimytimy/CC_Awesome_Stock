"""
政策事件追踪流水线。
对接任泽平（政策追踪）+ 高善文（货币/财政政策）框架。

设计原则：脚本只负责"抓取 + 归档"，不做政策影响判断。
影响判断由 skill 分析阶段的 LLM / industry-catalyst subagent 完成。

数据源（全部低封禁风险）：
- akshare news_cctv：新闻联播文字稿
- akshare news_economic_baidu：财经日历（经济数据公布）
- 国务院 / 发改委 / 央行 / 证监会官网：公开新闻列表（静态 HTML）
"""

from __future__ import annotations
import sys
import re
import time
import warnings
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

warnings.filterwarnings("ignore")

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "policy"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# ── 政府官网配置 ───────────────────────────────────────────
# 每个源：列表页 URL + base（用于补全相对链接）+ 链接特征
GOV_SOURCES = {
    "国务院": {
        "url": "https://www.gov.cn/zhengce/",
        "base": "https://www.gov.cn",
        "keywords": ["content", "zhengce"],
    },
    "发改委": {
        "url": "https://www.ndrc.gov.cn/xwdt/xwfb/",
        "base": "https://www.ndrc.gov.cn",
        "keywords": ["art", "/c"],
    },
    "央行": {
        "url": "http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html",
        "base": "http://www.pbc.gov.cn",
        "keywords": ["index.html", "goutongjiaoliu"],
    },
    "证监会": {
        "url": "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml",
        "base": "http://www.csrc.gov.cn",
        "keywords": ["content", "/c1", "art"],
    },
}


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def _is_fresh(fp: Path, ttl_hours: float) -> bool:
    return fp.exists() and (time.time() - fp.stat().st_mtime) / 3600 <= ttl_hours


# ────────────────────────────────────────────────────────────
# 1. 政府官网新闻列表
# ────────────────────────────────────────────────────────────

def fetch_gov_news(source_key: str, limit: int = 20) -> list[dict]:
    """
    抓取单个政府官网的新闻标题列表。
    返回：[{source, title, url}]
    只抓标题和链接，不抓正文（正文按需用 WebFetch 取）。
    """
    import requests
    from bs4 import BeautifulSoup

    cfg = GOV_SOURCES.get(source_key)
    if not cfg:
        return []

    try:
        resp = requests.get(cfg["url"], headers=_HEADERS, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[WARN] fetch_gov_news {source_key}: {e}", file=sys.stderr)
        return []

    # 导航/页脚类噪音标题，直接丢弃
    noise = ("English", "Version", "网站地图", "联系我们", "版权",
             "返回首页", "更多", "下一页", "上一页")

    items = []
    seen = set()
    for a in soup.select("a"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not title or len(title) < 10 or not href:
            continue
        if any(n in title for n in noise):
            continue
        # 链接特征过滤
        if not any(kw in href for kw in cfg["keywords"]):
            continue
        # 补全相对链接
        if href.startswith("/"):
            href = cfg["base"] + href
        elif not href.startswith("http"):
            href = cfg["url"].rsplit("/", 1)[0] + "/" + href
        if href in seen:
            continue
        seen.add(href)
        items.append({"source": source_key, "title": title, "url": href})
        if len(items) >= limit:
            break
    return items


def fetch_all_gov_news(limit_each: int = 15) -> list[dict]:
    """抓取全部政府官网新闻（加 random sleep 降频）。"""
    import random
    all_items = []
    for key in GOV_SOURCES:
        items = fetch_gov_news(key, limit=limit_each)
        all_items.extend(items)
        time.sleep(random.uniform(1.5, 3.5))  # 礼貌降频
    return all_items


# ────────────────────────────────────────────────────────────
# 2. 新闻联播（akshare）
# ────────────────────────────────────────────────────────────

def get_cctv_news(days: int = 5) -> list[dict]:
    """
    最近 N 天新闻联播文字稿。
    新闻联播的财经/政策报道是判断政策风向的高质量信源。
    返回：[{date, title, content}]
    """
    import akshare as ak
    results = []
    for i in range(days):
        d = (date.today() - timedelta(days=i)).strftime("%Y%m%d")
        try:
            df = ak.news_cctv(date=d)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    results.append({
                        "date": d,
                        "title": str(row.get("title", "")),
                        "content": str(row.get("content", ""))[:500],
                    })
        except Exception as e:
            print(f"[WARN] cctv_news {d}: {e}", file=sys.stderr)
        time.sleep(0.5)
    return results


# ────────────────────────────────────────────────────────────
# 3. 财经日历（akshare 百度）
# ────────────────────────────────────────────────────────────

# 只保留对 A 股有实际影响的重要经济数据
_CALENDAR_REGIONS = ("中国", "美国")
_CALENDAR_KEYWORDS = (
    "PMI", "CPI", "PPI", "GDP", "利率", "非农", "失业", "社融", "M2",
    "贷款", "进出口", "贸易", "零售", "工业", "通胀", "就业", "议息",
    "央行", "联储", "LPR", "MLF", "PCE",
)


def get_economic_calendar(days_back: int = 3, days_fwd: int = 7,
                          important_only: bool = True) -> list[dict]:
    """
    财经日历：经济数据公布时点 + 实际/预期值。
    用于提前知道"未来 N 天有哪些重要数据要公布"。
    important_only=True 时只保留中美重要数据（过滤掉全球细碎数据）。
    返回：[{date, time, region, event, actual, forecast}]
    """
    import akshare as ak
    results = []
    today = date.today()
    for i in range(-days_back, days_fwd + 1):
        d = (today + timedelta(days=i)).strftime("%Y%m%d")
        try:
            df = ak.news_economic_baidu(date=d)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    region = str(row.get("地区", ""))
                    event = str(row.get("事件", ""))
                    if important_only:
                        if not any(r in region for r in _CALENDAR_REGIONS):
                            continue
                        if not any(kw in event for kw in _CALENDAR_KEYWORDS):
                            continue
                    results.append({
                        "date": str(row.get("日期", d)),
                        "time": str(row.get("时间", "")),
                        "region": region,
                        "event": event,
                        "actual": str(row.get("公布", "")),
                        "forecast": str(row.get("预期", "")),
                    })
        except Exception as e:
            print(f"[WARN] econ_calendar {d}: {e}", file=sys.stderr)
        time.sleep(0.4)
    return results


# ────────────────────────────────────────────────────────────
# 4. 综合政策快照
# ────────────────────────────────────────────────────────────

def get_policy_snapshot(gov_limit: int = 15, cctv_days: int = 3) -> dict:
    """
    一次性聚合所有政策事件源。
    供 policy_track.py 归档使用。
    """
    return {
        "as_of": date.today().strftime("%Y-%m-%d"),
        "gov_news": fetch_all_gov_news(limit_each=gov_limit),
        "cctv_news": get_cctv_news(days=cctv_days),
        "economic_calendar": get_economic_calendar(days_back=2, days_fwd=7),
    }
