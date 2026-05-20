import types

import pandas as pd

from stock_data import company


def test_get_valuation_uses_baidu_stock_valuation(monkeypatch):
    calls = []

    def fake_stock_zh_valuation_baidu(symbol, indicator, period):
        calls.append((symbol, indicator, period))
        if indicator == "市盈率(TTM)":
            return pd.DataFrame({
                "date": pd.date_range("2026-01-01", periods=12),
                "value": list(range(10, 22)),
            })
        return pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=12),
            "value": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        })

    fake_ak = types.SimpleNamespace(stock_zh_valuation_baidu=fake_stock_zh_valuation_baidu)
    monkeypatch.setitem(__import__("sys").modules, "akshare", fake_ak)

    result = company.get_valuation("600519.SH")

    assert result["pe_ttm"] == 21.0
    assert result["pb"] == 12.0
    assert result["pe_percentile"] == 91.7
    assert result["source"] == "akshare.stock_zh_valuation_baidu"
    assert calls == [
        ("600519", "市盈率(TTM)", "近一年"),
        ("600519", "市净率", "近一年"),
    ]


def test_get_announcements_filters_recent_all_notices(monkeypatch):
    def fake_stock_individual_notice_report(security, symbol, begin_date, end_date):
        assert security == "600519"
        assert symbol == "全部"
        assert begin_date <= end_date
        return pd.DataFrame({
            "代码": ["600519", "600519"],
            "名称": ["贵州茅台", "贵州茅台"],
            "公告标题": ["股东大会", "一季报"],
            "公告类型": ["会议", "定期报告"],
            "公告日期": ["2026-05-19", "2026-05-20"],
        })

    fake_ak = types.SimpleNamespace(stock_individual_notice_report=fake_stock_individual_notice_report)
    monkeypatch.setitem(__import__("sys").modules, "akshare", fake_ak)

    result = company.get_announcements("600519.SH", limit=2)

    assert [row["公告标题"] for row in result] == ["一季报", "股东大会"]
    assert all(row["代码"] == "600519" for row in result)
