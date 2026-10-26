"""
build_database.py
-----------------
Loads the clean CSVs (data/clean/) into a DuckDB database using sql/schema.sql,
then runs a few checks so you know the data loaded correctly.

Run from the project root, after notebooks/03_cleaning_classification.ipynb:
    python src/build_database.py

The database file is data/gulfchem.duckdb. You can query it from Python:
    import duckdb
    con = duckdb.connect("data/gulfchem.duckdb")
    con.execute("SELECT * FROM v_po_line_detail LIMIT 5").fetchdf()
"""

import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "gulfchem.duckdb"


def main():
    os.chdir(ROOT)  # schema.sql uses paths relative to the project root
    con = duckdb.connect(str(DB_FILE))
    con.execute((ROOT / "sql" / "schema.sql").read_text())

    print("Tables loaded:")
    tables = con.execute("SELECT table_name FROM information_schema.tables ORDER BY table_name").fetchall()
    for (name,) in tables:
        rows = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchall()[0][0]
        print(f"  {name:<22} {rows:>8,} rows")

    print("\nChecks:")
    checks = {
        "PO lines without a supplier": "SELECT COUNT(*) FROM fact_po_line WHERE supplier_id IS NULL",
        "PO lines without a category": "SELECT COUNT(*) FROM fact_po_line WHERE category_code IS NULL",
        "PO lines without a receipt": """SELECT COUNT(*) FROM fact_po_line p LEFT JOIN fact_goods_receipt g
                                          USING (po_number, po_line) WHERE g.po_number IS NULL""",
        "PO lines without an invoice": """SELECT COUNT(*) FROM fact_po_line p LEFT JOIN fact_invoice i
                                           USING (po_number, po_line) WHERE i.po_number IS NULL""",
    }
    for label, sql in checks.items():
        print(f"  {label:<30} {con.execute(sql).fetchall()[0][0]}")

    print("\nSpend by year and category kind ($M):")
    summary = con.execute("""
        SELECT year, category_kind, ROUND(SUM(line_amount) / 1e6, 1) AS spend_musd
        FROM v_po_line_detail GROUP BY ALL ORDER BY year, category_kind
    """).fetchdf()
    print(summary.to_string(index=False))
    con.close()
    print(f"Database saved to {DB_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
