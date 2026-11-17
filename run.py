
# %%
import pandas as pd
import json
import argparse
from pathlib import Path


# %% 1. Find the Excel header row

def find_excel_header(file_path):
    preview = pd.read_excel(file_path, header=None)

    required_headers = {
        "order id",
        "symbol",
        "trade date",
        "quantity",
        "realized p&l"
    }

    for index, row in preview.iterrows():
        row_values = {
            str(value).strip().lower()
            for value in row
            if pd.notna(value)
        }

        if required_headers.issubset(row_values):
            return index

    raise ValueError(
        f"Could not find the header row in {file_path}"
    )


# %% 2. Load all MT5 CSV files

def load_mt5_files(data_dir):
    csv_files = sorted(Path(data_dir).glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            "No MT5 CSV files found in the data folder."
        )

    mt5_data = []

    required_columns = [
        "Ticket", "Type", "Symbol", "Close Time",
        "Volume", "Profit", "Commission", "Swap"
    ]

    for file_path in csv_files:
        df = pd.read_csv(file_path)

        missing_columns = [
            column for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing columns in {file_path}: {missing_columns}"
            )

        mt5_data.append(df)

    return pd.concat(mt5_data, ignore_index=True)


# %% 3. Load all broker Excel files

def load_broker_files(data_dir):
    excel_files = sorted(Path(data_dir).glob("*.xlsx"))

    if not excel_files:
        raise FileNotFoundError(
            "No broker Excel files found in the data folder."
        )

    broker_data = []

    required_columns = [
        "Order ID", "Symbol", "Trade Date",
        "Quantity", "Realized P&L"
    ]

    for file_path in excel_files:
        header_row = find_excel_header(file_path)

        df = pd.read_excel(
            file_path,
            header=header_row
        )

        df.columns = df.columns.astype(str).str.strip()

        missing_columns = [
            column for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing columns in {file_path}: {missing_columns}"
            )

        df = df.dropna(subset=["Order ID"])

        df = df[
            df["Order ID"].astype(str).str.strip().str.lower()
            != "total"
        ]

        broker_data.append(df)

    return pd.concat(broker_data, ignore_index=True)


# %% 4. Standardise MT5 data

def standardize_mt5(mt5_data):
    mt5_data = mt5_data.copy()

    mt5_data["Type"] = (
        mt5_data["Type"].astype(str).str.lower()
    )

    mt5_data = mt5_data[
        mt5_data["Type"].isin(["buy", "sell"])
    ]

    mt5_data = mt5_data.drop_duplicates(
        subset=["Ticket"],
        keep="first"
    )

    # Convert numeric columns
    numeric_columns = [
        "Profit", "Commission", "Swap", "Volume"
    ]

    for column in numeric_columns:
        original = mt5_data[column]

        converted = pd.to_numeric(
            original,
            errors="coerce"
        )

        invalid = original.notna() & converted.isna()

        if invalid.any():
            raise ValueError(
                f"Invalid numeric values found in MT5 column: {column}"
            )

        mt5_data[column] = converted

    # Blank Commission and Swap values represent zero
    mt5_data[["Commission", "Swap"]] = (
        mt5_data[["Commission", "Swap"]].fillna(0)
    )

    # Profit and Volume must be present
    if mt5_data[["Profit", "Volume"]].isna().any().any():
        raise ValueError(
            "MT5 data contains missing Profit or Volume values."
        )

    # Convert UTC closing time to IST
    mt5_data["Close Time"] = pd.to_datetime(
        mt5_data["Close Time"],
        format="%Y.%m.%d %H:%M:%S",
        utc=True,
        errors="raise"
    ).dt.tz_convert("Asia/Kolkata")

    # Calculate native P&L
    mt5_data["pnl_native"] = (
        mt5_data["Profit"]
        + mt5_data["Commission"]
        + mt5_data["Swap"]
    ).round(2)

    result = pd.DataFrame({
        "trade_id": "mt5-" + mt5_data["Ticket"].astype(str),
        "source": "mt5",
        "symbol": (
            mt5_data["Symbol"]
            .astype(str)
            .str.split(".", n=1)
            .str[0]
            .str.upper()
        ),
        "close_date": mt5_data["Close Time"].dt.strftime("%Y-%m-%d"),
        "close_time": mt5_data["Close Time"].dt.strftime("%H:%M:%S"),
        "quantity": mt5_data["Volume"],
        "pnl_native": mt5_data["pnl_native"],
        "currency": "USD"
    })

    return result


# %% 5. Standardise broker data

def standardize_broker(broker_data):
    broker_data = broker_data.copy()

    broker_data["trade_id"] = (
        "in-" + broker_data["Order ID"].astype(str)
    )

    broker_data["symbol"] = (
        broker_data["Symbol"]
        .astype(str)
        .str.split(".", n=1)
        .str[0]
        .str.upper()
    )

    broker_data["close_date"] = pd.to_datetime(
        broker_data["Trade Date"],
        format="%d-%m-%Y",
        errors="raise"
    ).dt.strftime("%Y-%m-%d")

    # Clean P&L values containing commas
    original_pnl = (
        broker_data["Realized P&L"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

    broker_data["pnl_native"] = pd.to_numeric(
        original_pnl,
        errors="coerce"
    ).round(2)

    broker_data["quantity"] = pd.to_numeric(
        broker_data["Quantity"],
        errors="coerce"
    )

    if broker_data[
        ["pnl_native", "quantity"]
    ].isna().any().any():
        raise ValueError(
            "Broker data contains missing or invalid numeric values."
        )

    result = pd.DataFrame({
        "trade_id": broker_data["trade_id"],
        "source": "broker_in",
        "symbol": broker_data["symbol"],
        "close_date": broker_data["close_date"],
        "close_time": "",
        "quantity": broker_data["quantity"],
        "pnl_native": broker_data["pnl_native"],
        "currency": "INR"
    })

    return result


# %% 6. Combine and classify trades

def combine_trades(mt5_data, broker_data, usd_inr):
    all_trades = pd.concat(
        [mt5_data, broker_data],
        ignore_index=True
    )

    all_trades["pnl_inr"] = (
        all_trades["pnl_native"]
        .where(
            all_trades["currency"] == "INR",
            all_trades["pnl_native"] * usd_inr
        )
    ).round(2)

    def classify_asset(symbol):
        symbol = str(symbol).upper()

        if symbol.startswith(("XAU", "XAG")):
            return "metals"

        elif symbol.startswith(("EUR", "GBP", "USD")):
            return "forex"

        elif symbol.startswith(("BTC", "ETH")):
            return "crypto"

        elif symbol.startswith(("NIFTY", "BANKNIFTY", "FINNIFTY")):
            return "index_options"

        else:
            return "other"

    all_trades["asset_class"] = (
        all_trades["symbol"].apply(classify_asset)
    )

    return all_trades


# %% 7. Create summary

def create_summary(all_trades):
    total_trades = len(all_trades)

    winning_trades = int(
        (all_trades["pnl_inr"] > 0).sum()
    )

    losing_trades = int(
        (all_trades["pnl_inr"] < 0).sum()
    )

    win_rate = (
        round(winning_trades / total_trades, 4)
        if total_trades else 0
    )

    net_pnl = round(
        all_trades["pnl_inr"].sum(), 2
    )

    asset_summary = all_trades.groupby("asset_class").agg(
        trades=("trade_id", "count"),
        net_pnl_inr=("pnl_inr", "sum")
    ).round(2)

    daily_summary = all_trades.groupby("close_date").agg(
        trades=("trade_id", "count"),
        net_pnl_inr=("pnl_inr", "sum")
    ).sort_index().round(2)

    daily_summary["cumulative_pnl_inr"] = (
        daily_summary["net_pnl_inr"].cumsum().round(2)
    )

    by_asset_class = {
        asset: {
            "trades": int(row["trades"]),
            "net_pnl_inr": round(float(row["net_pnl_inr"]), 2)
        }
        for asset, row in asset_summary.iterrows()
    }

    daily_records = [
        {
            "date": str(date),
            "trades": int(row["trades"]),
            "net_pnl_inr": round(float(row["net_pnl_inr"]), 2),
            "cumulative_pnl_inr": round(
                float(row["cumulative_pnl_inr"]), 2
            )
        }
        for date, row in daily_summary.iterrows()
    ]

    summary = {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": float(win_rate),
        "net_pnl_inr": float(net_pnl),
        "by_asset_class": by_asset_class,
        "daily": daily_records
    }

    return summary, daily_summary


# %% 8. Check trading-rule violations

def check_violations(all_trades, daily_summary, rules):
    violations = []

    for rule in rules:
        limit = rule["limit"]

        if rule["type"] == "max_trades_per_day":

            for date, row in daily_summary.iterrows():
                if row["trades"] > limit:
                    violations.append({
                        "date": date,
                        "rule_id": rule["id"],
                        "detail": (
                            f'{int(row["trades"])} trades exceeded '
                            f'daily limit of {limit}'
                        )
                    })

        elif rule["type"] == "max_daily_loss_inr":

            for date, row in daily_summary.iterrows():
                if row["net_pnl_inr"] < -limit:
                    violations.append({
                        "date": date,
                        "rule_id": rule["id"],
                        "detail": (
                            f'Daily loss of INR '
                            f'{abs(row["net_pnl_inr"]):.2f} '
                            f'exceeded limit of INR {limit}'
                        )
                    })

        elif rule["type"] == "stop_after_consecutive_losses":

            mt5_trades = all_trades[
                (all_trades["source"] == "mt5") &
                (all_trades["close_time"] != "")
            ].copy()

            mt5_trades = mt5_trades.sort_values(
                ["close_date", "close_time"]
            )

            for date, day_trades in mt5_trades.groupby("close_date"):
                loss_streak = 0

                for _, trade in day_trades.iterrows():

                    if loss_streak >= limit:
                        violations.append({
                            "date": date,
                            "rule_id": rule["id"],
                            "detail": (
                                f'Trade {trade["trade_id"]} taken '
                                f'after {limit} consecutive losses'
                            )
                        })
                        break

                    if trade["pnl_native"] < 0:
                        loss_streak += 1
                    else:
                        loss_streak = 0

        elif rule["type"] == "max_lot_size":

            mt5_trades = all_trades[
                all_trades["source"] == "mt5"
            ]

            oversized = mt5_trades[
                mt5_trades["quantity"] > limit
            ]

            for date, day_trades in oversized.groupby("close_date"):
                violations.append({
                    "date": date,
                    "rule_id": rule["id"],
                    "detail": (
                        f'{len(day_trades)} MT5 trades exceeded '
                        f'lot size limit of {limit}'
                    )
                })

    violations_df = pd.DataFrame(
        violations,
        columns=["date", "rule_id", "detail"]
    )

    violations_df = violations_df.sort_values(
        ["date", "rule_id"]
    ).reset_index(drop=True)

    return violations_df


# %% 9. Generate weekly discipline report

def generate_report(summary, violations_df):
    total = summary["total_trades"]
    net_pnl = summary["net_pnl_inr"]
    win_rate = summary["win_rate"]

    violation_count = len(violations_df)

    if net_pnl < 0:
        performance = (
            "The trader ended the period with a net loss."
        )

    elif net_pnl > 0:
        performance = (
            "The trader ended the period with a net profit."
        )

    else:
        performance = (
            "The trader broke even during this period."
        )

    if violation_count > 0:
        discipline = (
            f"The system detected {violation_count} rule violations. "
            "The trader should review these incidents and work on "
            "following their predefined limits."
        )

    else:
        discipline = (
            "No trading rule violations were detected."
        )

    report = f"""# Weekly Trading Discipline Report

## Performance Overview

- Total trades: {total}
- Win rate: {win_rate:.2%}
- Net P&L: INR {net_pnl:.2f}

{performance}

## Discipline Review

{discipline}

## Recommendation

Review losing trades carefully, maintain consistent risk management,
and avoid exceeding predefined trading limits.

Continue focusing on disciplined execution rather than chasing profits.
"""

    return report


# %% 10. Save all output files

def save_outputs(all_trades, summary, violations_df, report, out_dir):
    output_path = Path(out_dir)

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    final_columns = [
        "trade_id", "source", "symbol", "asset_class",
        "close_date", "close_time", "quantity",
        "pnl_native", "currency", "pnl_inr"
    ]

    all_trades[final_columns].to_csv(
        output_path / "trades.csv",
        index=False
    )

    with open(
        output_path / "summary.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            summary,
            file,
            indent=4
        )

    violations_df.to_csv(
        output_path / "violations.csv",
        index=False
    )

    with open(
        output_path / "report.md",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(report)

    print("All four output files created successfully!")


# %% 11. Main function

def main(data_dir, rules_file, out_dir):
    with open(
        rules_file,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    usd_inr = config["usd_inr"]
    rules = config["rules"]

    mt5_raw = load_mt5_files(data_dir)
    broker_raw = load_broker_files(data_dir)

    mt5_clean = standardize_mt5(mt5_raw)
    broker_clean = standardize_broker(broker_raw)

    all_trades = combine_trades(
        mt5_clean,
        broker_clean,
        usd_inr
    )

    summary, daily_summary = create_summary(all_trades)

    violations_df = check_violations(
        all_trades,
        daily_summary,
        rules
    )

    report = generate_report(
        summary,
        violations_df
    )

    save_outputs(
        all_trades,
        summary,
        violations_df,
        report,
        out_dir
    )


# %% 12. Command-line arguments

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TradeLens: Trading Performance and Rule Checker"
    )

    parser.add_argument(
        "--data",
        required=True,
        help="Input data folder"
    )

    parser.add_argument(
        "--rules",
        required=True,
        help="Path to rules.json"
    )

    parser.add_argument(
        "--out",
        required=True,
        help="Output folder"
    )

    args = parser.parse_args()

    main(
        args.data,
        args.rules,
        args.out
    )

# %%
