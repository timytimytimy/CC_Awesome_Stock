"""
巨潮资讯 cninfo 模块回归测试 —— 守住"官方原始源取数"的契约。
全程 mock akshare，不走网络。
"""

import sys
import types
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
if str(DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_ROOT))

from stock_data import cninfo  # noqa: E402


def _disclosure_df(rows):
    """构造 akshare 风格的公告 DataFrame。rows: [(title, date)]"""
    return pd.DataFrame([
        {"代码": "300769", "简称": "德方纳米", "公告标题": t,
         "公告时间": d, "公告链接": f"http://cninfo/{t}"}
        for t, d in rows
    ])


@pytest.fixture
def iso_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cninfo, "_CACHE_DIR", tmp_path)
    return tmp_path


# ════════════════════════════════════════════════════════════
# ticker 归一
# ════════════════════════════════════════════════════════════
def test_code_strips_exchange():
    assert cninfo._code("600519.SH") == "600519"
    assert cninfo._code("300769.SZ") == "300769"
    assert cninfo._code("688256") == "688256"


# ════════════════════════════════════════════════════════════
# 公告披露
# ════════════════════════════════════════════════════════════
def test_get_disclosures_renames_columns(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_zh_a_disclosure_report_cninfo=lambda **kw: _disclosure_df([
            ("德方纳米2025年年度报告", "2026-03-20"),
            ("德方纳米关于回购股份的公告", "2026-04-10"),
        ])
    )
    monkeypatch.setitem(sys.modules, "akshare", fake)
    df = cninfo.get_disclosures("300769.SZ", "20260101", "20260522")
    assert list(df.columns) == ["code", "name", "title", "date", "url"]
    assert len(df) == 2


def test_recent_disclosures_keyword_filter(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_zh_a_disclosure_report_cninfo=lambda **kw: _disclosure_df([
            ("2025年年度报告", "2026-03-20"),
            ("关于回购股份的公告", "2026-04-10"),
            ("关于股东减持的公告", "2026-04-15"),
        ])
    )
    monkeypatch.setitem(sys.modules, "akshare", fake)
    df = cninfo.recent_disclosures("300769.SZ", days=90, keyword="回购")
    assert len(df) == 1
    assert "回购" in df.iloc[0]["title"]


def test_get_disclosures_failsafe_on_error(iso_cache, monkeypatch):
    """akshare 抛异常（如空结果崩溃）→ 返回带列空表，不抛。"""
    def boom(**kw):
        raise KeyError("akshare 空结果 bug")
    monkeypatch.setitem(sys.modules, "akshare", types.SimpleNamespace(
        stock_zh_a_disclosure_report_cninfo=boom))
    df = cninfo.get_disclosures("300769.SZ", "20260101", "20260522")
    assert df.empty
    assert list(df.columns) == ["code", "name", "title", "date", "url"]


# ════════════════════════════════════════════════════════════
# 监管类风险公告
# ════════════════════════════════════════════════════════════
def test_find_inquiry_letters_catches_regulatory(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_zh_a_disclosure_report_cninfo=lambda **kw: _disclosure_df([
            ("2025年年度报告", "2026-03-20"),
            ("关于收到深圳证券交易所问询函的公告", "2026-04-01"),
            ("关于回复关注函的公告", "2026-04-20"),
        ])
    )
    monkeypatch.setitem(sys.modules, "akshare", fake)
    df = cninfo.find_inquiry_letters("300769.SZ", days=180)
    assert len(df) == 2          # 问询函 + 关注函
    titles = " ".join(df["title"])
    assert "问询函" in titles and "关注函" in titles


def test_find_inquiry_letters_clean_when_none(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_zh_a_disclosure_report_cninfo=lambda **kw: _disclosure_df([
            ("2025年年度报告", "2026-03-20"),
            ("关于回购股份的公告", "2026-04-10"),
        ])
    )
    monkeypatch.setitem(sys.modules, "akshare", fake)
    assert cninfo.find_inquiry_letters("300769.SZ", days=180).empty


# ════════════════════════════════════════════════════════════
# 招股说明书定位
# ════════════════════════════════════════════════════════════
def test_find_prospectus(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_profile_cninfo=lambda symbol: pd.DataFrame([{"上市日期": "2020-07-20"}]),
        stock_zh_a_disclosure_report_cninfo=lambda **kw: _disclosure_df([
            ("首次公开发行股票并在科创板上市招股说明书", "2020-07-14"),
            ("首次公开发行股票并在科创板上市招股意向书", "2020-07-01"),
            ("上市公告书", "2020-07-19"),
        ])
    )
    monkeypatch.setitem(sys.modules, "akshare", fake)
    pr = cninfo.find_prospectus("688256.SH")
    assert pr is not None
    assert "招股说明书" in pr["title"]   # 正式招股说明书优先于意向书


def test_find_prospectus_none_without_listing_date(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_profile_cninfo=lambda symbol: pd.DataFrame([{"上市日期": None}]))
    monkeypatch.setitem(sys.modules, "akshare", fake)
    assert cninfo.find_prospectus("688256.SH") is None


# ════════════════════════════════════════════════════════════
# 上市年数
# ════════════════════════════════════════════════════════════
def test_listing_years(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_profile_cninfo=lambda symbol: pd.DataFrame([{"上市日期": "2020-07-20"}]))
    monkeypatch.setitem(sys.modules, "akshare", fake)
    ly = cninfo.listing_years("688256.SH", today=date(2026, 5, 22))
    assert 5.5 < ly < 6.0       # 约 5.8 年


def test_listing_years_none_when_no_data(iso_cache, monkeypatch):
    fake = types.SimpleNamespace(
        stock_profile_cninfo=lambda symbol: pd.DataFrame())
    monkeypatch.setitem(sys.modules, "akshare", fake)
    assert cninfo.listing_years("688256.SH") is None
