-- AURELIA — load the backfill CSVs.
--   psql aurelia -v ON_ERROR_STOP=1 -f db/load_csv.sql
-- Run from the repo root (folder that contains data/). Safe to re-run: it starts a new load.

\set ON_ERROR_STOP on
BEGIN;

-- one advisory lock, so two loads can never overlap
SELECT pg_advisory_xact_lock(hashtext('aurelia_weekly_load'));

-- 1. open a load
INSERT INTO data_load (kind, status, week) VALUES ('backfill', 'loading', NULL);
CREATE TEMP TABLE cur ON COMMIT DROP AS SELECT max(load_id) AS id FROM data_load;

-- 2. stage the files exactly as they arrive
CREATE TEMP TABLE s_products (sku text, model text, department text, colour text,
    size text, price numeric, cost numeric, launch_date date, status text) ON COMMIT DROP;
CREATE TEMP TABLE s_sales (week text, sku text, channel text, units int,
    revenue numeric, discount_pct numeric) ON COMMIT DROP;
CREATE TEMP TABLE s_stock (week text, sku text, units_on_hand int) ON COMMIT DROP;
CREATE TEMP TABLE s_returns (week text, sku text, units_returned int, reason text) ON COMMIT DROP;
CREATE TEMP TABLE s_receipts (week text, sku text, units_received int,
    expected_date date, actual_date date) ON COMMIT DROP;
CREATE TEMP TABLE s_targets (month text, sku text, target_units int,
    target_revenue numeric, source_document text) ON COMMIT DROP;

\copy s_products FROM 'data/products.csv' WITH (FORMAT csv, HEADER true)
\copy s_sales    FROM 'data/sales.csv'    WITH (FORMAT csv, HEADER true)
\copy s_stock    FROM 'data/stock.csv'    WITH (FORMAT csv, HEADER true)
\copy s_returns  FROM 'data/returns.csv'  WITH (FORMAT csv, HEADER true)
\copy s_receipts FROM 'data/receipts.csv' WITH (FORMAT csv, HEADER true)
\copy s_targets  FROM 'data/targets.csv'  WITH (FORMAT csv, HEADER true)

-- 3. validate. any failure aborts the whole transaction.
DO $$
DECLARE n int;
BEGIN
    SELECT count(*) INTO n FROM s_sales WHERE week IS NULL OR sku IS NULL OR channel IS NULL;
    IF n > 0 THEN RAISE EXCEPTION 'sales: % rows with empty keys', n; END IF;

    SELECT count(*) INTO n FROM (
        SELECT week, sku, channel FROM s_sales GROUP BY 1,2,3 HAVING count(*) > 1) d;
    IF n > 0 THEN RAISE EXCEPTION 'sales: % duplicate week/sku/channel', n; END IF;

    SELECT count(*) INTO n FROM s_sales s
        LEFT JOIN s_products p USING (sku) WHERE p.sku IS NULL;
    IF n > 0 THEN RAISE EXCEPTION 'sales: % rows reference unknown SKU', n; END IF;

    -- dense tables: every SKU must appear in every week
    SELECT count(*) INTO n FROM (
        SELECT p.sku, w.week FROM s_products p
        CROSS JOIN (SELECT DISTINCT week FROM s_sales) w
        LEFT JOIN s_stock st ON st.sku = p.sku AND st.week = w.week
        WHERE st.sku IS NULL) g;
    IF n > 0 THEN RAISE EXCEPTION 'stock: % missing SKU/week combinations', n; END IF;

    -- sparse tables: referential check instead of coverage
    SELECT count(*) INTO n FROM s_returns r
        LEFT JOIN s_products p USING (sku) WHERE p.sku IS NULL;
    IF n > 0 THEN RAISE EXCEPTION 'returns: % rows reference unknown SKU', n; END IF;

    SELECT count(*) INTO n FROM s_sales WHERE units < 0 OR revenue < 0;
    IF n > 0 THEN RAISE EXCEPTION 'sales: % negative values', n; END IF;

    SELECT count(*) INTO n FROM s_sales s JOIN s_products p USING (sku)
        WHERE s.units > 0
          AND abs(s.revenue - s.units * p.price * (1 - s.discount_pct)) > 0.5;
    IF n > 0 THEN RAISE EXCEPTION 'sales: % rows where revenue does not reconcile', n; END IF;
END $$;

-- 4. move into the live tables
INSERT INTO products (sku, model, department, colour, size, price, cost,
                      launch_date, status, load_id)
SELECT sku, model, department, colour, NULLIF(size,''), price, cost,
       launch_date, status, (SELECT id FROM cur)
FROM s_products
ON CONFLICT (sku) DO UPDATE SET
    price = EXCLUDED.price, cost = EXCLUDED.cost,
    status = EXCLUDED.status, load_id = EXCLUDED.load_id;

INSERT INTO sales    SELECT week, sku, channel, units, revenue, discount_pct, (SELECT id FROM cur) FROM s_sales;
INSERT INTO stock    SELECT week, sku, units_on_hand, (SELECT id FROM cur) FROM s_stock;
INSERT INTO returns  SELECT week, sku, units_returned, reason, (SELECT id FROM cur) FROM s_returns;
INSERT INTO receipts SELECT week, sku, units_received, expected_date, actual_date, (SELECT id FROM cur) FROM s_receipts;
INSERT INTO targets  SELECT month, sku, target_units, target_revenue, source_document, (SELECT id FROM cur) FROM s_targets;

-- 5. retire any earlier backfill, so the views never return a row twice.
--    (weekly incremental loads stay published side by side; a backfill replaces
--     everything before it)
UPDATE data_load
   SET status = 'superseded'
 WHERE status = 'published'
   AND kind   = 'backfill'
   AND load_id <> (SELECT id FROM cur);

-- 6. publish. nothing above was visible until this line.
UPDATE data_load SET
    status = 'published',
    published_at = now(),
    row_counts = jsonb_build_object(
        'products', (SELECT count(*) FROM s_products),
        'sales',    (SELECT count(*) FROM s_sales),
        'stock',    (SELECT count(*) FROM s_stock),
        'returns',  (SELECT count(*) FROM s_returns),
        'receipts', (SELECT count(*) FROM s_receipts),
        'targets',  (SELECT count(*) FROM s_targets)),
    checks_passed = '["keys","duplicates","referential","dense_coverage","non_negative","revenue_reconciles"]'::jsonb
WHERE load_id = (SELECT id FROM cur);

COMMIT;

\echo ''
\echo '=== loaded ==='
SELECT load_id, status, row_counts, published_at FROM data_load ORDER BY load_id DESC LIMIT 1;
SELECT (SELECT count(*) FROM v_sales) AS sales,
       (SELECT count(*) FROM v_stock) AS stock,
       (SELECT count(*) FROM v_targets) AS targets;
