# ministats

A tiny CLI that reads a one-column CSV of numbers and prints summary
statistics.

## Usage

```
python -m cli.main data/sample.csv --format json
python -m cli.main data/sample.csv --format text
```

## Output contracts (also enforced by `tests/test_cli.py`)

1. **JSON key**: the JSON output uses the key `sum` for the total
   (not `total`, not `total_sum`).
2. **Integer fidelity**: when all input values are integers, the JSON
   `sum` value is an integer (e.g. `5`), not a float (`5.0`).
3. **Mean precision**: any displayed `mean` value is formatted with
   exactly 2 decimal places (e.g. `2.00`).

There are currently three failing behaviors that violate these
contracts.

## Test suite

```
python -m pytest tests/ -q
```
