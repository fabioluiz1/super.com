# Interview Script — Cheat Sheet

---

## Phase 1: Present the Scaffold (0–2 min)

**Do it yourself:**
```bash
docker compose up -d db
mise run dev:backend
curl localhost:8000/health
```
Open `localhost:8000/docs` in browser.

**Say out loud:**
> "The scaffold uses mise for tool versions and tasks — everything is `mise run <task>`. A pre-commit hook runs ruff, mypy strict, and pytest on every commit, so AI-generated code that doesn't pass gets rejected automatically. FastAPI is async-native — one process handles hundreds of concurrent requests. Postgres runs in Docker for dev and tests — a separate `super_test` database isolates test data. Each test gets a fresh schema. The ORM is SQLAlchemy 2.0 with typed models, and Alembic handles migrations. CLAUDE.md codifies my conventions so the AI follows them from the start."

Point at the project tree. Don't explain. End with:
> "No models, routes, or business logic yet — that's what we'll build together."

---

## Round 1 — Load CSV, Models, CRUD (~2–40 min)

### Step 1: Inspect the CSV

**Do it yourself:**
```python
python
>>> import pandas as pd
>>> df = pd.read_csv("deals.csv")
>>> df
>>> df["hotel_phone"].nunique()
>>> df.dtypes
>>> df.groupby("hotel_phone")[["hotel_name","hotel_city","hotel_country"]].nunique().max()

# Extract unique hotels now — reused in Step 5 for loading
>>> hotels = (df[['hotel_name', 'hotel_city', 'hotel_country', 'hotel_phone']]
...           .drop_duplicates(subset=['hotel_phone'])
...           .rename(columns=lambda c: c.replace('hotel_', '')))
>>> print(f"{len(hotels)} unique hotels")  # → 150
```

**Say out loud:**
> "50,000 rows, 15 columns, 150 unique hotels. Phone uniquely identifies a hotel — confirmed by the groupby. I've already extracted a clean hotels DataFrame; I'll reuse it when loading data. I'll normalize into `hotels` and `deals` tables with a 1:N relationship."

**Ask interviewer:**
- Flat or normalized?
- Unique key: `(name, city, country)` or `phone`?
- Check constraints at DB level? (star 1–5, prices > 0, discount 0–100, checkout > checkin)

### Step 2: Create SQLAlchemy models

**Say out loud:**
> "I'll ask Claude to create two models: Hotel and Deal. Deal has a hotel_id FK. The CSV doesn't have hotel_id — I'll handle that in the loader script."

**Delegate to Claude (plan mode):**
> "Create two SQLAlchemy models: Hotel and Deal. [paste ER diagram]. Add unique constraint (name, city, country). Add check constraints: star_rating 1–5, price_per_night > 0, original_price > 0, discount_percent 0–100, checkout_date > checkin_date."

**Review aloud:**
- Unique constraint on `(name, city, country)`
- FK `hotel_id` non-nullable with index
- Types match CSV — decimal for prices, date for dates, bool for is_available
- Bidirectional relationship with `back_populates`
- No business logic in models

### Step 3: Migration

**Say out loud:**
> "Models look good. I'll generate the Alembic migration and inspect it before applying — I never blindly run migrations."

**Do it yourself:**
```bash
mise run db:generate "create hotels and deals tables"
```

**Review the migration file aloud:**
- Two `create_table` calls — `hotels` first (parent), then `deals` (child)
- FK constraint on `hotel_id` → `hotels.id`
- Check constraints present
- `downgrade()` drops in reverse order

**Do it yourself:**
```bash
mise run db:migrate
```

Verify in DBeaver: tables exist, FKs exist, check constraints exist, no rows.

**If interviewer asks for changes** — rollback, delete the migration, fix model, re-generate:
```bash
mise run db:rollback
rm alembic/versions/<hash>_create_hotels_and_deals_tables.py
# fix the model
mise run db:generate "create hotels and deals tables"
mise run db:migrate
```

**Commit:** `feat: add hotel and deal models with 1:N relationship and alembic migration`

### Step 4: Integration tests for models

**Say out loud:**
> "Let's add integration tests — they hit a real Postgres database, so they verify the full stack: ORM mapping, FK constraints, and check constraints. These aren't unit tests — we're testing DB-level behavior, not mocking it."

**Delegate to Claude:**
> "Add integration tests for hotel and deal models: create via ORM, verify 1:N relationship both directions (hotel.deals, deal.hotel). Test check constraints reject invalid data — negative price, star_rating outside 1–5, checkout before checkin — raise IntegrityError."

**Do it yourself:**
```bash
mise run test:backend && mise run typecheck:backend
```

**Commit:** `test: add model integration tests for ORM relationships and check constraints`

### Step 5: Load CSV data

**Say out loud:**
> "The CSV has hotel names, not hotel IDs — so I can't insert deals directly. But instead of writing a loader script with ORM inserts and flush-for-IDs, I'll treat this as a data wrangling problem: pandas to extract hotels, load them with `to_sql`, query the generated IDs back, merge into deals, and load deals — all in one REPL session."

**Do it yourself** (Python REPL — pure pandas, SQLAlchemy only as DB adapter):
```python
# pd, df, hotels already in REPL from Step 1
from sqlalchemy import create_engine  # required by pandas for DB access
db = create_engine('postgresql://super@localhost:5432/super')

# Hotels: already extracted in Step 1 — load directly
print(hotels.to_sql('hotels', db, if_exists='append', index=False, method='multi'), "hotels inserted")  # → 150

# Deals: resolve hotel_id via merge on phone, load
hotel_ids = pd.read_sql("SELECT id AS hotel_id, phone FROM hotels", db)
deals = (df.merge(hotel_ids, left_on='hotel_phone', right_on='phone')
         .rename(columns={'hotel_star_rating': 'rating'})
         [['hotel_id', 'rating', 'room_type', 'price_per_night', 'original_price',
           'discount_percent', 'checkin_date', 'checkout_date', 'is_available',
           'categories', 'created_at']])
print(deals.to_sql('deals', db, if_exists='append', index=False, method='multi', chunksize=1000), "deals inserted")  # → 50000
```

**Verify in DBeaver / psql:**
```sql
SELECT count(*) FROM hotels;  -- → 150
SELECT count(*) FROM deals;   -- → 50000
SELECT h.name, d.room_type, d.price_per_night
FROM deals d JOIN hotels h ON d.hotel_id = h.id LIMIT 3;
```

**Say out loud (why this approach):**
> "I turned a code problem into a data problem. The FK resolution is just a pandas merge on phone. `to_sql` with `method='multi'` batches into multi-row INSERTs — fast enough for 50k rows. No ORM boilerplate, no intermediate files, one REPL session. For millions of rows I'd load the raw CSV into a staging table with `to_sql`, then `INSERT INTO deals SELECT ... FROM staging_deals JOIN hotels USING (phone)` — FK resolution stays in the database."

**Commit:** `feat: load CSV data via pandas (extract hotels, resolve FKs, bulk insert)`

### Step 6: CRUD endpoints (READ: list + detail)

**Say out loud:**
> "You'll notice my prompt is just the requirement. That's because my CLAUDE.md specifies the layered architecture — schemas, repositories, services, routers — and testing preferences. Let me show you."
> *(Open CLAUDE.md, scroll to Layered Architecture)*

**Delegate to Claude (plan mode):**
> "Create list and detail endpoints for deals. Each deal includes hotel info. Use structured error responses: `{"error": {"code": "NOT_FOUND", "message": "..."}}`. Add integration tests."

**Do it yourself:**
```bash
mise run test:backend && mise run typecheck:backend
```

Test in Swagger UI: list deals, get single deal, get non-existent ID → 404.

**Review aloud:**
- `from_attributes=True` on Pydantic response schemas
- Response schemas only — no request body for read endpoints
- `selectinload(Deal.hotel)` — NOT lazy loading
- Repositories return models, no HTTP concepts
- Routers use `DB` alias (`Annotated[AsyncSession, Depends(get_db)]`)
- Tests use `httpx.AsyncClient` (not sync TestClient)

**Say out loud (N+1):**
> "Let me check SQL logs. If I see 21 queries for 20 deals, that's N+1. Fix: `selectinload(Deal.hotel)` — 2 queries total."

**Commit:** `feat: add list and detail endpoints for deals with eager loading`

### Step 7: Update CLAUDE.md

**Do it yourself** — add to CLAUDE.md:
```markdown
### API Conventions
- Always use selectinload() — never lazy loading (N+1)
- Deal responses always include nested hotel data
- Services raise HTTPException — repositories never raise HTTP errors
```

**Say out loud:**
> "I'm adding this rule so the AI never generates lazy-loaded code again."

**Commit:** `docs: update CLAUDE.md with API conventions and eager loading rule`

---

## Round 2 — Write Operations (~15 min in)

**Say out loud:**
> "POST /deals (201), PATCH /deals/{id} (200, partial update), DELETE /deals/{id} (204). Create needs hotel_id validation — clear 404 before FK constraint error. PATCH sends only changed fields (all Optional). Delete — hard or soft?"

**Ask interviewer:** "Soft delete or hard delete?"

**Delegate to Claude (plan mode):**
> "Add create, update, delete for deals. Create validates hotel_id exists (404 if not), returns 201. PATCH with all-optional fields. Delete returns 204. Add Pydantic `@field_validator` rules on request schemas: price > 0, discount 0–100, checkout > checkin. Integration tests including invalid hotel_id, non-existent IDs, Pydantic validation rejects invalid input."

**Do it yourself:**
```bash
mise run test:backend && mise run typecheck:backend
```

Test in Swagger: POST valid → 201, POST bad hotel_id → 404, POST with `price_per_night: -50` → 422, PATCH → 200, DELETE → 204, GET deleted → 404.

**Say out loud (two validation layers):**
> "Pydantic validates API input — 422 before hitting the DB. Check constraints are the safety net for anything that bypasses the API. Both enforce the same rules but serve different purposes."

**Say out loud (transactions):**
> "get_db gives each request its own session. Changes flush in a single transaction at the end. If the endpoint raises, session rolls back. For multi-write atomicity: `async with db.begin()`. Never call db.commit() mid-endpoint."

**If asked about concurrent updates:**
> "Optimistic locking — add a version column, `WHERE id = :id AND version = :v`. 0 rows affected = 409 Conflict. Client retries."

**Commit:** `feat: add create, update, delete endpoints for deals`

---

## Round 3 — Filtering (~30 min in)

**Pause 15–30 seconds. Then say out loud:**
> "This impacts repository (WHERE clauses), schema (query params), router (new params). Model doesn't change. I'll write the filters myself — it's a few lines, AI would be slower."

> "Query params: `city` (string, on hotels table — needs JOIN), `min_stars` (int, on hotels), `price_min`/`price_max` (on deals). All optional. I'll also add indexes on filtered columns — city, star_rating, price_per_night."

**Do it yourself** — write the WHERE clauses and query params.

**If asked "What about case-sensitive city search?":**
> "Quick fix: `ilike()` — works but can't use indexes. Production: functional index on `lower(city)`, then `WHERE lower(city) = lower(:input)`."

**Do it yourself:**
```bash
mise run test:backend && mise run typecheck:backend
```

Test in Swagger: `?city=Toronto`, `?min_stars=4`, `?price_min=50&price_max=150`, combined, no filters → all.

**Commit:** `feat: add filtering by city, star rating, and price range`

---

## Round 4 — Pagination (~40 min in)

**Say out loud:**
> "Offset-based with `skip`/`limit`, default limit=20, return `total` count. Two caveats: OFFSET is O(n) for deep pages — cursor pagination with PK is O(log n) for production. COUNT(*) is expensive on large Postgres tables — alternatives: Redis cache, `pg_class` reltuples, or 'has next page' (fetch limit+1)."

**Do it yourself or delegate** — depends on complexity.

```bash
mise run test:backend && mise run typecheck:backend
```

Test: `?skip=0&limit=5`, `?skip=5&limit=5`, large skip → empty results + correct total.

**Commit:** `feat: add offset-based pagination with total count`

---

## Round 5 — Aggregation (~50 min in)

**Say out loud:**
> "GET /deals/stats → [{city, avg_price, deal_count}]. JOIN deals ON hotels, GROUP BY city, func.avg(), func.count(), ORDER BY deal_count DESC."

**Ask interviewer:** "Real-time or stale-OK? If stale, I'd cache in Redis with a TTL."

**Delegate to Claude:**
> "Add stats endpoint: avg price per night and deal count by city. JOIN, GROUP BY, sort by deal count desc. Integration tests with known fixture data."

```bash
mise run test:backend && mise run typecheck:backend
```

**Commit:** `feat: add stats endpoint with avg price and deal count by city`

---

## Round 6 — Normalize Categories (~60 min in)

**Pause. Say out loud:**
> "Right now categories is comma-separated text — LIKE '%luxury%' is slow and fragile. I need to:
> 1. Create `categories` table (id, name unique)
> 2. Create `deal_categories` association table
> 3. Add M:N relationship on Deal
> 4. Data migration: split text → rows, deduplicate, wire association table
> 5. Update list endpoint with `category` filter via JOIN
> 6. Add `selectinload(Deal.categories)` to avoid N+1"

**Delegate to Claude (plan mode):**
> Full prompt with all 6 steps above.

```bash
mise run test:backend && mise run typecheck:backend
```

Verify in DBeaver: `SELECT count(*) FROM categories` → 5, `SELECT count(*) FROM deal_categories` → ~80000.

**Update CLAUDE.md** with query patterns.

**Commit:** `feat: normalize categories into M:N with data migration`

---

## Round 7 — Performance Discussion (~75 min in)

**Say out loud:**
> "I'd measure, not guess. Four things to check in order:"

1. **N+1** — SQL echo shows flood of identical queries → `selectinload()` fix
2. **Missing indexes** — `EXPLAIN ANALYZE` shows `Seq Scan` → add indexes
3. **Connection pool exhaustion** — `pg_stat_activity` shows `idle in transaction` → kill sessions, tune pool, PgBouncer
4. **Table bloat** — `pg_stat_user_tables` shows high dead tuple % → `VACUUM ANALYZE`

> "Diagnose before optimizing. Adding indexes for a pool problem wastes time."

---

## Phase 3: Show Version History (last 2 min)

**Do it yourself:**
```bash
git log --oneline
```

**Say out loud:**
> "Each commit is one logical change. If I need to revert categories, it's one `git revert`. The log reads like a changelog."

**Volunteer improvements:**
1. Domain events (Kafka for pub/sub, Celery for single tasks)
2. Write buffering for high-throughput (Redis/Kafka → batch INSERT ON CONFLICT)
3. Rate limiting / caching on stats
4. Cursor-based pagination
5. Database scaling ladder: indexes → PgBouncer → Redis cache → read replicas → partitioning → materialized views → sharding
6. OpenAPI enrichment (summary, description, tags)
7. Factory Boy for test factories

---

## Commands to Memorize

```bash
# Start
docker compose up -d db
mise run dev:backend

# DB migrations
mise run db:generate "message"
mise run db:migrate
mise run db:rollback

# Guardrails (run after EVERY change)
mise run test:backend && mise run typecheck:backend

# Load data (pandas REPL — see Step 5)
# hotels.to_sql() + merge hotel_id + deals.to_sql(method='multi')

# Verify data
psql -h localhost -U super -d super

# CSV inspection
python
>>> import pandas as pd
>>> df = pd.read_csv("deals.csv")
>>> df
>>> df["hotel_phone"].nunique()
>>> df.dtypes
>>> df.groupby("hotel_phone")[["hotel_name","hotel_city","hotel_country"]].nunique().max()
```

---

## SQL to Memorize (DBeaver / psql)

```sql
-- Row counts
SELECT count(*) FROM hotels;
SELECT count(*) FROM deals;

-- Verify FK join
SELECT h.name, h.city, d.room_type, d.price_per_night
FROM deals d JOIN hotels h ON d.hotel_id = h.id LIMIT 3;

-- Verify indexes
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename IN ('hotels','deals') AND indexname NOT LIKE 'pk_%';

-- Categories after normalization
SELECT count(*) FROM categories;
SELECT count(*) FROM deal_categories;

-- Performance debugging
EXPLAIN ANALYZE SELECT ... ;
SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';
SELECT relname, seq_scan, idx_scan FROM pg_stat_user_tables;
SELECT relname, n_live_tup, n_dead_tup FROM pg_stat_user_tables;
```

---

## Decision Table: AI or Manual?

| Task | Do |
|------|----|
| New model + migration + full CRUD | Claude (plan mode) |
| Load CSV with FK resolution | Yourself — pandas `to_sql` + merge |
| Add WHERE clause to existing query | Yourself (2 lines) |
| Add query param to endpoint | Yourself (1 line router + 1 repo) |
| New relationship + association table + migration | Claude (plan mode) |
| Fix a typo or import | Yourself |
| Debug failing test | Read error yourself, explain aloud, then decide |

---

## Interview Loop (every feature from Round 1 Step 5 onward)

1. **RESTATE** requirement aloud
2. **TELL** interviewer what you'll ask Claude to do
3. **PROMPT** Claude (plan mode for multi-file)
4. **VERIFY** — `mise run test:backend && mise run typecheck:backend` + Swagger UI
5. **REVIEW** generated code aloud
6. **ADJUST** if needed, re-run guardrails
7. **COMMIT**
8. **NARRATE** what you'd improve with more time
