
import pandas as pd

from run import (
    combine_trades,
    standardize_mt5,
    create_summary
)


# Test 1: Asset classification

def test_asset_classification():
    mt5_data = pd.DataFrame({
        "trade_id": ["mt5-1", "mt5-2", "mt5-3", "mt5-4", "mt5-5"],
        "source": ["mt5"] * 5,
        "symbol": ["XAUUSD", "EURUSD", "BTCUSD", "NIFTY", "AAPL"],
        "close_date": ["2026-09-07"] * 5,
        "close_time": ["10:00:00"] * 5,
        "quantity": [1, 1, 1, 1, 1],
        "pnl_native": [10, 10, 10, 10, 10],
        "currency": ["USD"] * 5
    })

    broker_data = pd.DataFrame(columns=mt5_data.columns)

    result = combine_trades(mt5_data, broker_data, 84)

    assert result["asset_class"].tolist() == [
        "metals",
        "forex",
        "crypto",
        "index_options",
        "other"
    ]


# Test 2: MT5 data standardisation

def test_standardize_mt5():
    raw_data = pd.DataFrame({
        "Ticket": [12345, 12346],
        "Type": ["buy", "balance"],
        "Symbol": ["XAUUSD.a", "EURUSD"],
        "Close Time": [
            "2026.09.07 10:00:00",
            "2026.09.07 11:00:00"
        ],
        "Volume": [1.0, 0],
        "Profit": [100, 0],
        "Commission": [-2, 0],
        "Swap": [-1, 0]
    })

    result = standardize_mt5(raw_data)

    assert len(result) == 1
    assert result.iloc[0]["trade_id"] == "mt5-12345"
    assert result.iloc[0]["symbol"] == "XAUUSD"
    assert result.iloc[0]["pnl_native"] == 97
    assert result.iloc[0]["currency"] == "USD"


# Test 3: Summary calculations

def test_create_summary():
    trades = pd.DataFrame({
        "trade_id": ["mt5-1", "mt5-2", "in-3"],
        "source": ["mt5", "mt5", "broker_in"],
        "symbol": ["XAUUSD", "EURUSD", "BTCUSD"],
        "asset_class": ["metals", "forex", "crypto"],
        "close_date": [
            "2026-09-07",
            "2026-09-07",
            "2026-09-08"
        ],
        "close_time": ["10:00:00", "11:00:00", ""],
        "quantity": [1, 1, 2],
        "pnl_native": [100, -50, 200],
        "currency": ["USD", "USD", "INR"],
        "pnl_inr": [8400, -4200, 200]
    })

    summary, daily = create_summary(trades)

    assert summary["total_trades"] == 3
    assert summary["winning_trades"] == 2
    assert summary["losing_trades"] == 1
    assert summary["win_rate"] == 0.6667
    assert summary["net_pnl_inr"] == 4400
    assert len(daily) == 2
