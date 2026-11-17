# TradeLens – Trading Performance & Rule Checker

A Python command-line application that combines trading records from MetaTrader 5 (MT5) CSV files and Indian broker Excel statements into a standardised dataset.

TradeLens calculates trading performance, generates daily and asset-class summaries, and checks whether trades follow predefined risk-management rules.

## Features

- Reads multiple MT5 CSV and broker Excel files.
- Automatically detects the broker Excel header row.
- Removes duplicate MT5 trades and skips non-trade transactions.
- Converts MT5 timestamps from UTC to Indian Standard Time (IST).
- Calculates P&L in INR using the exchange rate provided in `rules.json`.
- Classifies trades by asset class.
- Generates trading performance summaries.
- Detects trading-rule violations using configurable limits.
- Generates a weekly discipline report without requiring an API key.

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
└── AI_USAGE.md
```

## Installation

Clone the repository:

```bash
git clone <your-github-repository-url>
cd TradeLens
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## How to Run

Execute the following command from the project root:

```bash
python run.py --data sample/data --rules sample/rules.json --out output
```

The program reads the input files and creates the output folder automatically.

## Output Files

The application generates four files:

| File | Description |
|---|---|
| `trades.csv` | Standardised trading records from all sources |
| `summary.json` | Overall, asset-class and daily performance statistics |
| `violations.csv` | Detected trading-rule violations |
| `report.md` | Weekly trading discipline report |

## Trading Rules

The application supports configurable rules defined in `rules.json`:

- Maximum trades per day.
- Maximum daily loss in INR.
- Stop trading after consecutive losses.
- Maximum MT5 lot size.

Rule limits and the USD-to-INR exchange rate are read from the configuration file rather than hardcoded.

## Running Tests

Run the automated tests using:

```bash
python -m pytest -v
```

The test suite covers asset classification, MT5 data standardisation and summary calculations.

## Future Improvements

With more development time, I would like to:

- Add more test cases for edge cases and different input formats.
- Integrate an optional LLM API for more detailed and personalised trading discipline reports.
- Add visualisations for daily P&L and trading performance.
- Improve error handling and validation for inconsistent input files.

## Author

Developed as part of the Python Developer Intern assignment at Coding Pocket IT Solutions.