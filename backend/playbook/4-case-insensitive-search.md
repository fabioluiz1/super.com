# Case-Insensitive Search in PostgreSQL + SQLAlchemy

When the interviewer asks: "What if someone searches for 'toronto' but the data says 'Toronto'?"

---

## Three approaches, ranked

### 1. `ilike` — the quick fix

PostgreSQL's `ILIKE` operator is `LIKE` but case-insensitive. SQLAlchemy exposes it directly:

```python
select(Hotel).where(Hotel.city.ilike(f"%{city}%"))
```

- Works immediately — no migration, no index
- **Problem**: `ILIKE` with a leading `%` can't use a regular B-tree index — it's a sequential scan on every row. Fine for 50k rows, unacceptable for millions

### 2. `func.lower()` — still slow without an index

Wrap both sides in `lower()` so the comparison is case-insensitive:

```python
from sqlalchemy import func

select(Hotel).where(func.lower(Hotel.city) == func.lower(city))
```

- Generates: `WHERE lower(city) = lower('toronto')`
- **Problem**: `lower(city)` is a computed expression — a regular B-tree index on `city` won't help. It's still a sequential scan unless you add a functional index

### 3. `func.lower()` + functional index — the production answer

Add a functional index that pre-computes `lower(city)`:

```python
# In the Alembic migration
op.create_index("ix_hotels_city_lower", "hotels", [sa.text("lower(city)")])
```

Now `WHERE lower(city) = lower('toronto')` hits the index — O(log n) lookup instead of a sequential scan.

```sql
-- What PostgreSQL sees
EXPLAIN ANALYZE SELECT * FROM hotels WHERE lower(city) = lower('toronto');
-- → Index Scan using ix_hotels_city_lower (cost=0.28..8.30 rows=1)
```

## What to say in the interview

> "I'll use `ilike` for the interview — it's the simplest and correct. But without a functional index, it's a sequential scan. In production with millions of rows, I'd add a functional index on `lower(city)` so PostgreSQL can use an index scan. Let me show you."
>
> *Add the index in the Alembic migration, then run `EXPLAIN ANALYZE` to prove it works.*

If the interviewer asks about partial matches ("tor" matching "Toronto"):

> "That's a `LIKE` / `contains` pattern: `Hotel.city.ilike(f'%{query}%')`. Leading wildcards can't use B-tree indexes at all — even functional ones. For production prefix search, I'd use a trigram index (`pg_trgm` extension + GIN index) or full-text search. But for exact city matching, the functional index on `lower()` is the right answer."

## Comparison table

| Approach | Case-insensitive | Indexed | Migration needed |
|---|---|---|---|
| `ilike('%toronto%')` | Yes | No (seq scan) | No |
| `func.lower() == func.lower()` | Yes | No (seq scan) | No |
| `func.lower()` + functional index | Yes | Yes (index scan) | Yes |
| `citext` column type | Yes | Yes (regular index) | Yes (extension + migration) |
| Trigram GIN index (`pg_trgm`) | Yes (partial too) | Yes | Yes (extension + migration) |

## Bonus: `citext` — the "just make the column case-insensitive" approach

PostgreSQL has a `citext` (case-insensitive text) extension. If you define the column as `citext`, all comparisons are automatically case-insensitive — no `lower()`, no `ilike()`:

```sql
CREATE EXTENSION IF NOT EXISTS citext;
ALTER TABLE hotels ALTER COLUMN city TYPE citext;

-- Now this just works:
SELECT * FROM hotels WHERE city = 'toronto';  -- matches 'Toronto'
```

- Regular B-tree indexes work on `citext` columns
- Downside: requires the `citext` extension (not available on all managed Postgres providers), and it's a schema-level decision — you're changing the column type, not just the query

Good to mention as an alternative, but `func.lower()` + functional index is the safer answer because it doesn't require changing column types or enabling extensions.
