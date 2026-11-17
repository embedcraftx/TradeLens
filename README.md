# TradeLens – Trading Performance & Rule Checker

TradeLens is a Python command-line application that combines trading records from MetaTrader 5 (MT5) CSV files and Indian broker Excel statements into a standardised dataset.

It analyses trading performance, generates daily and asset-class summaries, and checks whether trades follow predefined risk-management rules.

## Features

- Reads multiple MT5 CSV and broker Excel files.
- Automatically detects the broker Excel header row.
- Removes duplicate MT5 trades and skips non-trade transactions.
- Converts MT5 timestamps from UTC to Indian Standard Time (IST).
- Calculates P&L in INR using the exchange rate provided in `rules.json`.
- Classifies trades into metals, forex, crypto, index options and other asset classes.
- Generates overall, daily and asset-class performance summaries.
- Detects trading-rule violations using configurable limits.
- Generates a weekly trading discipline report without requiring an API key.

## Technologies Used

- Python 3.10+
- Pandas
- OpenPyXL
- Pytest

## Project Structure

```text
TradeLens/
│
├── sample/
│   ├── data/
│   │   ├── mt5_history_part1.csv
│   │   ├── mt5_history_part2.csv
│   │   └── broker_pnl_inr.xlsx
│   └── rules.json
│
├── tests/
│   └── test_tradelens.py
│
├── run.py
├── requirements.txt
├── README.md
├── AI_USAGE.md
└── .gitignore
```

## Installation

Clone the repository:

```bash
git clone https://github.com/embedcraftx/TradeLens.git
cd TradeLens
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## How to Run

Execute the following command from the project root:

```bash
python run.py --data sample/data --rules sample/rules.json --out output
```

The program automatically creates the output directory and generates the required files.

## Output Files

The application generates four files:

| File | Description |
|---|---|
| `trades.csv` | Standardised trading records from all sources |
| `summary.json` | Overall, asset-class and daily performance statistics |
| `violations.csv` | Detected trading-rule violations |
| `report.md` | Weekly trading discipline report |

## Trading Rules

The application supports four configurable trading rules defined in `rules.json`:

- **Maximum trades per day:** Detects when the daily trade count exceeds the configured limit.
- **Maximum daily loss:** Detects when the total daily loss exceeds the configured INR limit.
- **Consecutive losses:** Detects trades taken after a specified number of consecutive losing MT5 trades.
- **Maximum lot size:** Detects MT5 trades exceeding the configured lot-size limit.

Rule limits and the USD-to-INR exchange rate are read from the configuration file rather than hardcoded.

## Running Tests

Run the automated test suite using:

```bash
python -m pytest -v
```

The test suite currently includes three tests covering:

- Asset-class classification.
- MT5 data standardisation.
- Trading performance summary calculations.

## Future Improvements

With more development time, I would like to:

- Expand test coverage for edge cases and different input formats.
- Integrate an optional LLM API for more detailed and personalised trading discipline reports.
- Add visualisations for daily P&L and trading performance.
- Improve error handling and validation for inconsistent input files.

## AI Usage

AI assistance during development is documented in [AI_USAGE.md](AI_USAGE.md).

## Author

Developed as part of the Python Developer Intern assignment at Coding Pocket IT Solutions.

## Repository

[GitHub – TradeLens](https://github.com/embedcraftx/TradeLens)