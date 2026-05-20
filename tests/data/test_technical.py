import sys
import types

import pandas as pd

from stock_data import technical


def test_compute_rps_subtracts_benchmark_return(monkeypatch):
    stock_df = pd.DataFrame({
        "日期": pd.date_range("2026-01-01", periods=5),
        "收盘": [100, 105, 110, 120, 130],
    })
    benchmark_df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=5),
        "close": [100, 100, 105, 105, 110],
    })

    def fake_get_kline(ticker, period):
        assert ticker == "600519.SH"
        return stock_df.tail(period)

    fake_ak = types.SimpleNamespace(stock_zh_index_daily=lambda symbol: benchmark_df)
    monkeypatch.setitem(sys.modules, "akshare", fake_ak)
    monkeypatch.setattr("stock_data.company.get_kline", fake_get_kline)

    result = technical.compute_rps("600519.SH", periods=(5,))

    assert result["stock_returns"]["5d"] == 30.0
    assert result["benchmark_returns"]["5d"] == 10.0
    assert result["rps_scores"]["5d"] == 20.0


def test_compute_rps_falls_back_to_stock_return_when_benchmark_missing(monkeypatch):
    stock_df = pd.DataFrame({
        "日期": pd.date_range("2026-01-01", periods=3),
        "收盘": [100, 110, 121],
    })

    monkeypatch.setattr("stock_data.company.get_kline", lambda ticker, period: stock_df)
    monkeypatch.setattr(technical, "_get_benchmark_kline", lambda benchmark, period: pd.DataFrame())

    result = technical.compute_rps("600519.SH", periods=(3,))

    assert result["benchmark_error"] == "no benchmark kline"
    assert result["rps_scores"]["3d"] == 21.0
