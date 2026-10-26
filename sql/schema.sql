-- ===========================================================================
-- GulfChem maintenance spend: star schema (DuckDB)
-- Dimensions describe the "who, what, where, when"; facts hold the events.
-- Built by src/build_database.py from the clean CSVs in data/clean/.
-- ===========================================================================

-- ---------- Dimensions ----------
CREATE OR REPLACE TABLE dim_site AS
SELECT site_id, site_name, state, size_factor,
       CAST(turnaround_start AS DATE) AS turnaround_start, turnaround_days
FROM read_csv_auto('data/clean/sites.csv');

CREATE OR REPLACE TABLE dim_category AS
SELECT category_code, category_name, kind
FROM read_csv_auto('data/clean/categories.csv');

CREATE OR REPLACE TABLE dim_supplier AS
SELECT * FROM read_csv_auto('data/clean/suppliers.csv');

CREATE OR REPLACE TABLE dim_vendor AS       -- vendor record -> real supplier
SELECT * FROM read_csv_auto('data/clean/vendor_xref.csv');

CREATE OR REPLACE TABLE dim_material AS
SELECT * FROM read_csv_auto('data/clean/item_master.csv');

CREATE OR REPLACE TABLE dim_contract AS
SELECT * FROM read_csv_auto('data/clean/contracts.csv');

CREATE OR REPLACE TABLE contract_rates AS
SELECT * FROM read_csv_auto('data/clean/contract_rates.csv');

-- One row per calendar day, so any fact can be grouped by month, quarter or year
CREATE OR REPLACE TABLE dim_date AS
SELECT d::DATE AS date_key,
       year(d) AS year, quarter(d) AS quarter, month(d) AS month,
       strftime(d, '%Y-%m') AS year_month, strftime(d, '%b') AS month_name
FROM range(DATE '2022-12-01', DATE '2026-04-01', INTERVAL 1 DAY) AS t(d);

-- ---------- Facts ----------
CREATE OR REPLACE TABLE fact_po_line AS
SELECT * FROM read_csv_auto('data/clean/po_lines.csv', types={'po_number': 'VARCHAR'});

CREATE OR REPLACE TABLE fact_goods_receipt AS
SELECT * FROM read_csv_auto('data/clean/goods_receipts.csv', types={'po_number': 'VARCHAR'});

CREATE OR REPLACE TABLE fact_invoice AS
SELECT * FROM read_csv_auto('data/clean/invoices.csv', types={'po_number': 'VARCHAR'});

CREATE OR REPLACE TABLE equipment AS SELECT * FROM read_csv_auto('data/clean/equipment.csv');
CREATE OR REPLACE TABLE work_orders AS SELECT * FROM read_csv_auto('data/clean/work_orders.csv');
CREATE OR REPLACE TABLE wo_parts AS SELECT * FROM read_csv_auto('data/clean/wo_parts.csv');

-- ---------- A convenient analysis view: one row per PO line with everything joined ----------
CREATE OR REPLACE VIEW v_po_line_detail AS
SELECT p.*,
       s.site_name, s.state AS site_state,
       c.category_name, c.kind AS category_kind,
       sup.supplier_name, sup.status AS supplier_status,
       d.year, d.quarter, d.year_month,
       g.promised_date, g.actual_date, g.qty_received, g.qty_rejected,
       (g.actual_date > g.promised_date) AS delivered_late
FROM fact_po_line p
LEFT JOIN dim_site s      ON p.site_id = s.site_id
LEFT JOIN dim_category c  ON p.category_code = c.category_code
LEFT JOIN dim_supplier sup ON p.supplier_id = sup.supplier_id
LEFT JOIN dim_date d      ON p.po_date = d.date_key
LEFT JOIN fact_goods_receipt g ON p.po_number = g.po_number AND p.po_line = g.po_line;
