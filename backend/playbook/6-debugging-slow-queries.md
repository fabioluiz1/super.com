# Debugging Slow Queries in PostgreSQL + FastAPI

When the interviewer asks "the endpoint is slow, walk me through it" — lead with the approach, not the answer.

---

## The approach: don't guess, measure

> "Before optimizing anything, I need to identify the actual bottleneck. I'd check four things in order: application logs, query plans, connection pool state, and table health."

---

## Symptom 1: N+1 queries

**How you notice it**: SQL logs show a flood of nearly identical queries.

```
# structlog output — 21 queries for a 20-item page
SELECT * FROM deals LIMIT 20 OFFSET 0                  -- 1 query
SELECT * FROM categories WHERE deal_id = 1              -- +1
SELECT * FROM categories WHERE deal_id = 2              -- +1
SELECT * FROM categories WHERE deal_id = 3              -- +1
...                                                     -- × 20
```

**How to debug**:

1. **Enable SQL echo** in development — SQLAlchemy's `echo=True` on the engine prints every query:
   ```python
   engine = create_async_engine(DATABASE_URL, echo=True)
   ```

2. **Count queries per request** — structlog with the request ID middleware lets you grep logs:
   ```bash
   # Count queries for a single request
   grep "request_id=abc123" app.log | grep "SELECT" | wc -l
   # 21 ← should be 2
   ```

3. **In production** — use `pg_stat_statements` to find queries with high `calls` count relative to the endpoint's request rate:
   ```sql
   SELECT query, calls, mean_exec_time
   FROM pg_stat_statements
   ORDER BY calls DESC
   LIMIT 10;
   ```

**Fix**: `selectinload(Deal.categories)` — reduces N+1 to 2 queries (one for deals, one for all related categories in a single `WHERE deal_id IN (...)`).

---

## Symptom 2: Missing indexes (sequential scans)

**How you notice it**: a single query is slow, not many queries.

**How to debug**:

1. **`EXPLAIN ANALYZE`** — shows the actual execution plan and timing:
   ```sql
   EXPLAIN ANALYZE
   SELECT d.* FROM deals d
   JOIN hotels h ON d.hotel_id = h.id
   WHERE h.city = 'Toronto' AND d.price_per_night < 100;
   ```

2. **Read the plan** — look for `Seq Scan` (bad) vs `Index Scan` (good):
   ```
   -- BAD: sequential scan — reads every row
   Seq Scan on deals  (cost=0.00..1234.00 rows=50000 width=64) (actual time=0.01..45.23 rows=50000)
     Filter: (price_per_night < 100)
     Rows Removed by Filter: 40000

   -- GOOD: index scan — jumps directly to matching rows
   Index Scan using ix_deals_price_per_night on deals  (cost=0.29..8.31 rows=10000 width=64) (actual time=0.02..1.15 rows=10000)
     Index Cond: (price_per_night < 100)
   ```

3. **Check which indexes exist**:
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'deals';
   ```

4. **Find missing indexes** — PostgreSQL tracks sequential scans per table:
   ```sql
   SELECT relname, seq_scan, idx_scan,
          seq_scan - idx_scan AS too_many_seq_scans
   FROM pg_stat_user_tables
   WHERE seq_scan > idx_scan
   ORDER BY too_many_seq_scans DESC;
   ```
   Tables with `seq_scan >> idx_scan` are missing indexes on commonly filtered columns.

**Fix**: add indexes on columns used in `WHERE`, `JOIN`, and `ORDER BY`:
```sql
CREATE INDEX ix_hotels_city ON hotels (city);
CREATE INDEX ix_deals_hotel_id ON deals (hotel_id);
CREATE INDEX ix_deals_price_per_night ON deals (price_per_night);
CREATE INDEX ix_deals_is_available ON deals (is_available);
-- For the M:N join table — composite indexes on both FKs
CREATE INDEX ix_deal_categories_deal_id ON deal_categories (deal_id);
CREATE INDEX ix_deal_categories_category_id ON deal_categories (category_id);
```

---

## Symptom 3: Connection pool exhaustion

**How you notice it**: requests hang or timeout, but the database itself is fine. The app logs show `TimeoutError` or `QueuePool limit of 15 overflow 10 reached`.

**How to debug**:

1. **Check active connections from PostgreSQL's side**:
   ```sql
   -- How many connections, grouped by state
   SELECT state, count(*)
   FROM pg_stat_activity
   WHERE datname = 'super'
   GROUP BY state;

   -- state  | count
   -- active |     5    ← running queries right now
   -- idle   |    10    ← connected but doing nothing (held by the pool)
   -- idle in transaction | 3  ← BAD: these hold locks and block others
   ```

2. **Find long-running queries**:
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE datname = 'super'
     AND state != 'idle'
   ORDER BY duration DESC;
   ```

3. **Find "idle in transaction" — the silent killer**:
   ```sql
   SELECT pid, now() - xact_start AS transaction_duration, query
   FROM pg_stat_activity
   WHERE state = 'idle in transaction'
     AND datname = 'super';
   ```
   These are sessions that started a transaction but never committed or rolled back. They hold locks, consume a connection, and block other queries. Usually caused by a missing `async with session:` block or an exception that skips the commit/rollback.

4. **Check pool stats from the application** — SQLAlchemy exposes pool state:
   ```python
   from app.db.session import engine
   pool = engine.pool
   print(f"Pool size: {pool.size()}")
   print(f"Checked out: {pool.checkedout()}")
   print(f"Overflow: {pool.overflow()}")
   print(f"Checked in: {pool.checkedin()}")
   ```

**Fix**:
- Short term: increase `pool_size` and `max_overflow` in `config.py`
- Kill idle-in-transaction sessions: `SELECT pg_terminate_backend(pid)`
- Ensure every session is properly closed (FastAPI's `get_db()` dependency handles this)
- Long term: use PgBouncer for connection multiplexing across multiple app instances

---

## Symptom 4: Slow deep pagination

**How you notice it**: pages 1–10 are fast, page 500 is slow.

**How to debug**:

1. **`EXPLAIN ANALYZE` with a deep offset**:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM deals ORDER BY id LIMIT 20 OFFSET 10000;

   -- Limit  (actual time=25.12..25.15 rows=20)
   --   → Sort  (actual time=25.10..25.12 rows=10020)
   --       Sort Key: id
   --       → Seq Scan on deals  (actual time=0.01..15.00 rows=50000)
   ```
   Postgres scans and sorts 10,020 rows just to return 20. At offset 100,000 this becomes very expensive.

2. **Compare with cursor-based**:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM deals WHERE id > 10000 ORDER BY id LIMIT 20;

   -- Limit  (actual time=0.03..0.05 rows=20)
   --   → Index Scan using pk_deals on deals  (actual time=0.02..0.04 rows=20)
   --       Index Cond: (id > 10000)
   ```
   O(log n) index seek — constant time regardless of how deep into the dataset.

**Fix**: cursor-based pagination (`WHERE id > last_seen_id LIMIT 20`) for deep pages. Keep offset for shallow pages where simplicity matters.

---

## Symptom 5: Table bloat (dead tuples)

**How you notice it**: queries gradually get slower over time even though the data size hasn't changed much. `EXPLAIN ANALYZE` shows the table is much larger than expected.

**How to debug**:

1. **Check dead tuple count**:
   ```sql
   SELECT relname, n_live_tup, n_dead_tup,
          round(n_dead_tup::numeric / greatest(n_live_tup, 1) * 100, 1) AS dead_pct,
          last_vacuum, last_autovacuum
   FROM pg_stat_user_tables
   WHERE relname IN ('deals', 'hotels', 'deal_categories')
   ORDER BY n_dead_tup DESC;

   -- relname | n_live_tup | n_dead_tup | dead_pct | last_autovacuum
   -- deals   |      50000 |      25000 |     50.0 | 2025-01-15 03:00:00  ← 50% dead rows!
   ```

2. **Check table size vs expected size**:
   ```sql
   SELECT relname,
          pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
          pg_size_pretty(pg_relation_size(relid)) AS table_size,
          pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS index_size
   FROM pg_stat_user_tables
   WHERE relname = 'deals';
   ```

**Why this happens**: PostgreSQL uses MVCC (Multi-Version Concurrency Control). When you `UPDATE` or `DELETE` a row, the old version isn't immediately removed — it's marked as a "dead tuple." Autovacuum reclaims dead tuples periodically, but if it can't keep up (high write volume, or autovacuum is misconfigured), dead tuples accumulate. Queries must scan past dead rows, and indexes point to dead entries, making both slower.

**Fix**:
- Check autovacuum is running: `SHOW autovacuum;` → should be `on`
- Manual vacuum for immediate relief: `VACUUM ANALYZE deals;`
- For severe bloat: `VACUUM FULL deals;` (rewrites the table — locks it, use off-peak)
- Tune autovacuum for high-write tables:
  ```sql
  ALTER TABLE deals SET (autovacuum_vacuum_scale_factor = 0.05);  -- vacuum at 5% dead (default 20%)
  ALTER TABLE deals SET (autovacuum_analyze_scale_factor = 0.02); -- analyze at 2% change
  ```

---

## What to say in the interview

> "I wouldn't guess — I'd measure. First, I'd check the application logs for N+1 patterns (a flood of identical queries). Then `EXPLAIN ANALYZE` on the slow query to see if it's a sequential scan that needs an index. If the query itself is fast but requests are timing out, I'd check `pg_stat_activity` for connection pool exhaustion or idle-in-transaction sessions. And if performance degrades over time without data growth, I'd check dead tuple counts — the table might need vacuuming.
>
> The key principle is: diagnose before optimizing. Adding indexes for a connection pool problem or adding a cache for a missing index wastes time and hides the real issue."
