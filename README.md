## ETL-Style Data Transform Tool (SQLAlchemy + Pandas)

This project is a small ETL-style tool that:

- **Loads** data from Excel (`.xlsx`) or SQL files (with `INSERT` statements)
- **Transforms/cleans** the data (column lookups via database, removals, computed columns, required defaults)
- **Outputs** a clean SQL file with `INSERT INTO table_name (...) VALUES (...);` statements ready to import.

### Features

- **SQLAlchemy ORM** models and session factory
- **Excel loader** (`excel_loader.py`) using pandas
- **SQL loader** (`sql_loader.py`) that parses `INSERT` statements into a `DataFrame`
- **Transformation engine** (`transformer.py`) with:
  - `replace_column_with_lookup`
  - `remove_columns`
  - `add_computed_column`
  - `add_missing_columns`
- **SQL writer** (`sql_writer.py`) for generating clean SQL
- **CLI entrypoint** (`main.py`) that:
  - Detects Excel vs SQL input
  - Applies transformations defined in `config.py`
  - Writes final SQL to an output file

---

## Project Structure

```text
data-transform/
  README.md
  requirements.txt
  config.py
  main.py
  db.py
  models.py
  excel_loader.py
  sql_loader.py
  transformer.py
  sql_writer.py
  example_data/
    customers_example.csv
    customers_example_output.sql
```

> Note: The example input is provided as CSV for convenience. You can open it in Excel and save as `customers_example.xlsx` to test the Excel loader.

---

## Installation

1. **Create/activate virtualenv** (you already have one in this repo, but for completeness):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Set database URL**

The tool uses SQLAlchemy with a database URL from the `DATABASE_URL` environment variable.

For example, to use a local SQLite file:

```bash
export DATABASE_URL="sqlite:///./example.db"
```

You can create and populate this database using `models.py` as a reference (see below).

---

## Defining Database Models & Seed Data

The project includes an example `Customer` model in `models.py`:

- `id` (primary key)
- `tin`
- `first_name`
- `last_name`

You can create the tables and seed some data by running a small script in the Python REPL:

```bash
python
```

```python
from db import Base, engine, get_session
from models import Customer

Base.metadata.create_all(bind=engine)

with get_session() as session:
    # Add a sample customer
    c = Customer(tin="123-45-6789", first_name="John", last_name="Doe")
    session.add(c)
    session.commit()
    print("Customer ID:", c.id)
```

Make sure the `DATABASE_URL` is set before running this.

---

## Example Transformations (in `config.py`)

The file `config.py` defines transformation rules per table name.

For `customers`, the default example includes:

- **Replace** `customer_tin` with `customer_id` via DB lookup on the `Customer` model.
- **Remove** unwanted columns (`temp_column`, `unused_flag`).
- **Add** computed column `full_name = first_name + " " + last_name`.
- **Ensure** required column `created_at` exists, defaulting to `datetime.utcnow()`.

You can customize or extend these rules in `config.py`.

---

## Running the Tool

### 1. From Excel Input

Assume you have `customers_example.xlsx` with columns like:

- `customer_tin`
- `first_name`
- `last_name`
- `temp_column`
- `unused_flag`

Run:

```bash
python main.py \
  --input-file example_data/customers_example.xlsx \
  --table-name customers \
  --output-file example_data/customers_cleaned.sql
```

The script will:

- Detect Excel from file extension
- Load into a DataFrame
- Apply the configured transformations for `customers`
- Produce `INSERT` statements into `customers_cleaned.sql`

### 2. From SQL Input

If you have a file `customers_raw.sql` containing:

```sql
INSERT INTO customers (customer_tin, first_name, last_name, temp_column) VALUES ('123-45-6789', 'John', 'Doe', 'x');
```

Run:

```bash
python main.py \
  --input-file customers_raw.sql \
  --table-name customers \
  --output-file customers_cleaned.sql
```

The SQL loader will parse the statements, feed them through the same transformation pipeline, and then re-generate clean SQL.

---

## Example Input and Output

### Example CSV (for Excel)

See `example_data/customers_example.csv` for a simple example dataset. Open it with Excel and save as `customers_example.xlsx` if you want to test the Excel loader.

### Example Output SQL

An example output is provided in `example_data/customers_example_output.sql`. Your exact IDs/timestamps may differ depending on your database contents.

---

## CLI Options

```bash
python main.py --help
```

Key options:

- `--input-file`: Path to `.xlsx` or `.sql` input file (required)
- `--table-name`: Target table name for output `INSERT` statements (required)
- `--output-file`: Path to write the cleaned SQL output file (required)

---

## Notes

- The transformation engine is intentionally generic; you can import and call the functions directly in your own scripts.
- `config.py` is only one way to define transformations; you can write your own logic in `main.py` or other modules if desired.


