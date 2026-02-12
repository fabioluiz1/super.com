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

**Do it yourself** — `mise run python` preloads `pd` and `db` via PYTHONSTARTUP:
```bash
mise run python
```
```python
>>> df = pd.read_csv("deals.csv")
>>> df
>>> df.dtypes
>>> df["hotel_phone"].nunique()  # → 150
>>> df.groupby("hotel_phone")[["hotel_name","hotel_city","hotel_country"]].nunique().max()

# star_rating is a deal property, not a hotel property
>>> df.groupby("hotel_phone")["hotel_star_rating"].value_counts().unstack(fill_value=0)
# each hotel has deals with ALL star ratings — it's per-deal, not per-hotel

# Extract unique hotels now — reused in Step 3 for loading
>>> hotel_columns = ['hotel_name', 'hotel_city', 'hotel_country', 'hotel_phone']
>>> hotels = (df[hotel_columns]
...           .drop_duplicates(subset=['hotel_phone'])
...           .rename(columns=lambda c: c.replace('hotel_', '')))
>>> print(f"{len(hotels)} unique hotels")  # → 150
```

**Say out loud:**
> "50,000 rows, 15 columns, 150 unique hotels. Phone uniquely identifies a hotel — confirmed by the groupby. star_rating varies per deal within the same hotel, so it's a deal property, not a hotel property. I'll normalize into `hotels` and `deals` tables with a 1:N relationship."

**Ask interviewer:**
- Flat or normalized?
- Unique key: `(name, city, country)` or `phone`?
- The CSV `id` column — preserve as `external_id` or let DB auto-generate?
- Check constraints at DB level? (star 1–5, prices > 0, discount 0–100, checkout > checkin)

### Step 2: Create SQLAlchemy models + migration + tests

**Say out loud:**
> "I'll ask Claude to create two models: Hotel and Deal. Deal has a `hotel_id` FK and keeps `star_rating` since it varies per deal. `external_id` preserves the CSV's original ID separately from the auto-increment PK."

**Delegate to Claude (plan mode):**
> "Create two SQLAlchemy models: Hotel and Deal. [paste ER diagram]. `external_id` unique on Deal. Add unique constraint (name, city, country) on Hotel. Add check constraints: star_rating 1–5, price_per_night > 0, original_price > 0, discount_percent 0–100, checkout_date > checkin_date."

**Review aloud:**
- Unique constraint on `(name, city, country)`
- FK `hotel_id` non-nullable with index
- `external_id` unique — preserves CSV ID, doesn't desync PK sequence
- Types match CSV — decimal for prices, date for dates, bool for is_available
- Bidirectional relationship with `back_populates`
- No business logic in models

**Generate and review migration:**
```bash
mise run db:generate "create hotels and deals tables"
```
- Two `create_table` calls — `hotels` first (parent), then `deals` (child)
- FK constraint, check constraints present, `downgrade()` drops in reverse order

```bash
mise run db:migrate
```
Verify in DBeaver: tables exist, FKs, check constraints, no rows.

**Integration tests** — delegate to Claude:
> "Add integration tests: create via ORM, verify 1:N both directions, check constraints reject invalid data — raise IntegrityError."

```bash
mise run test:backend && mise run typecheck:backend
```

**Commits:**
- `feat: add hotel and deal models with 1:N relationship and alembic migration`
- `test: add model integration tests for ORM relationships and check constraints`

### Step 3: Load CSV data

**Say out loud:**
> "The CSV has hotel names, not hotel IDs — so I can't insert deals directly. I'll treat this as a data wrangling problem: pandas to extract hotels, load them with `to_sql`, query the generated IDs back, merge into deals, and load deals — all in one REPL session."

**Do it yourself** — `pd`, `db`, `df`, `hotels`, `hotel_columns` already in REPL:
```python
# Hotels: already extracted — load directly
hotels.to_sql('hotels', db, if_exists='append', index=False)  # → 150

# Deals: resolve hotel_id via merge on phone, load
hotel_ids = pd.read_sql("SELECT id AS hotel_id, phone AS hotel_phone FROM hotels", db)
deals = (df.merge(hotel_ids)  # auto-joins on 'hotel_phone'
           .rename(columns={'id': 'external_id', 'hotel_star_rating': 'star_rating'})
           .drop(columns=hotel_columns))
deals.to_sql('deals', db, if_exists='append', index=False, method='multi')  # → 50000
```

**Verify:**
```sql
SELECT count(*) FROM hotels;  -- → 150
SELECT count(*) FROM deals;   -- → 50000
SELECT h.name, h.city, d.room_type, d.price_per_night
FROM deals d JOIN hotels h ON d.hotel_id = h.id LIMIT 3;
```

**Say out loud:**
> "I turned a code problem into a data problem. The FK resolution is just a pandas merge on phone. `to_sql` with `method='multi'` batches into multi-row INSERTs — fast enough for 50k rows. For millions of rows I'd load into a staging table, then `INSERT INTO deals SELECT ... FROM staging JOIN hotels USING (phone)` — FK resolution stays in the database."

**Commit:** `feat: load CSV data via pandas (extract hotels, resolve FKs, bulk insert)`

### Step 4: List endpoint

**Say out loud:**
> "Before I start, let me show you the backend architecture I documented."
> *(Open architecture.md — show the Layers section.)*
> "Each request flows through four layers: schema, repository, service, router. Because these decisions are written down, I can delegate to Claude Code and review against these standards."

**Delegate to Claude (plan mode):**
> "Create a list endpoint for deals (`GET /deals`). Each deal response includes hotel info (name, city, country, avg_star_rating). `avg_star_rating` is a computed field — the average of `star_rating` across all deals for that hotel. Use structured error responses: `{"error": {"code": "...", "message": "..."}}`. Add integration tests."

```bash
mise run test:backend && mise run typecheck:backend
```

**Review aloud:**
- **DI** — endpoint receives `db: DB`, not a manually created session
- **Repository** — uses `selectinload(Deal.hotel)` (NOT lazy loading)
- **Schema** — `HotelResponse` nested inside `DealResponse`, `avg_star_rating` included
- **Tests** — happy path + empty DB returns `[]`

**Optional:** detail endpoint (`GET /deals/{id}`) — ask interviewer if they want it now.

**Commit:** `feat: add list endpoint for deals with eager loading`

### Step 5: Update CLAUDE.md

**Do it yourself** — add to CLAUDE.md:
```markdown
### API Conventions
- Always use selectinload() — never lazy loading (N+1)
- Deal responses always include nested hotel data
- Services raise domain exceptions (NotFoundError) — never HTTPException
```

> "I'm adding this rule so the AI never generates lazy-loaded code again."

**Commit:** `docs: update CLAUDE.md with API conventions and eager loading rule`

---

## Round 2 — Write Operations (~25 min in)

**Restate:**
> "Three write endpoints for deals: create, update, delete. Create needs `hotel_id` in the request body — the service validates it exists before inserting."

**Ask interviewer:** "Soft delete or hard delete?"

Architecture handles the rest — see architecture.md for status codes, PATCH vs PUT, validation.

**Delegate to Claude (plan mode):**
> "Add create, update, and delete endpoints for deals. Create takes `hotel_id` in the request body."

```bash
mise run test:backend && mise run typecheck:backend
```

Test in Swagger: POST valid → 201, POST bad hotel_id → 404, POST `price: -50` → 422, PATCH → 200, DELETE → 204.

**Say out loud (transactions):**
> "get_db commits on success, rolls back on exception. Autobegin means all operations in a request are already in one transaction — multi-entity writes are atomic by default. Never db.commit() or db.begin() in services."

**Say out loud (validation):**
> "Pydantic validates API input — 422 before hitting the DB. Check constraints are the safety net for anything that bypasses the API. Both enforce the same rules but serve different purposes."

**If asked about concurrent updates:**
> "SQLAlchemy has built-in optimistic locking via `version_id_col` — auto WHERE, auto increment, raises StaleDataError. Service catches it, returns 409 Conflict."

**Commit:** `feat: add create, update, and delete endpoints for deals`

---

## Round 3 — Filtering (~45 min in)

**Pause 15–30 seconds. Then say out loud:**

> "I need to add filtering to the list endpoint. Four optional query params:
> - `city` — string, lives on `hotels` → query joins through `Deal.hotel`
> - `min_stars` — int, but Hotel has no `star_rating` column today. I need to add a stored `star_rating` on Hotel, computed as `AVG(deals.star_rating)`. The deal service recalculates it on every deal create/update/delete — app-level, not a DB trigger. That means a new migration + backfill.
> - `price_min` / `price_max` — Decimal, directly on `deals.price_per_night`
>
> Indexes on every filtered column: `city` and `star_rating` on `hotels`, `price_per_night` on `deals`."

**Build:**
- **Model + Migration**: add `star_rating: Mapped[Decimal]` to Hotel, migration with backfill from `AVG(deals.star_rating)`, indexes
- **Repository**: WHERE clauses + helper to recalculate hotel star_rating
- **Service**: forward filter params; recalculate `hotel.star_rating` after deal create/update/delete
- **Router**: 4 optional `Query` params

```bash
mise run test:backend && mise run typecheck:backend
```

Test in Swagger: `?city=Toronto`, `?min_stars=4`, `?price_min=50&price_max=150`, combined, no filters → all.

**If asked "What about case-sensitive city search?":**
> "Functional index on `lower(city)`, then `WHERE lower(city) = lower(:input)`. For substring search: trigram index (`pg_trgm` + GIN)."

**Commit:** `feat: add filtering by city, star rating, and price range`

---

## Round 4 — Pagination (~60 min in)

**Pause. Say out loud:**

> "Offset-based with `skip`/`limit`, default limit=20, return `total` count.
> Two caveats: OFFSET is O(n) for deep pages — cursor pagination with PK is O(log n). COUNT(*) is expensive on large Postgres tables — alternatives: Redis cache, `pg_class` reltuples, 'has next page' (fetch limit+1).
> The scaffold already has `PaginatedResponse[T]` and `Paginated[T]` — I'll wire them in."

**Build:**
- **Schema**: `DealListResponse = PaginatedResponse[DealResponse]`
- **Service**: return `Paginated[Deal]` with items, total, skip, limit
- **Router**: `skip: int = Query(0, ge=0)`, `limit: int = Query(20, ge=1, le=100)`

```bash
mise run test:backend && mise run typecheck:backend
```

Test: `?skip=0&limit=5`, `?skip=5&limit=5`, large skip → empty + correct total, pagination with filters.

**Commit:** `feat: add offset-based pagination with total count`

---

## Round 5 — Aggregation (~70 min in)

**Pause. Say out loud:**

> "`GET /deals/stats` → `[{city, avg_price, deal_count}]`. JOIN deals ON hotels, GROUP BY city, `func.avg()`, `func.count()`, ORDER BY deal_count DESC."

**Ask interviewer:** "Real-time or stale-OK? If stale, I'd cache in Redis with a TTL."

**Build:**
- **Schema**: `CityStatsResponse` — city, avg_price, deal_count
- **Repository**: JOIN + GROUP BY + func.avg + func.count + ORDER BY
- **Router**: `GET /deals/stats` → `list[CityStatsResponse]`, status 200

```bash
mise run test:backend && mise run typecheck:backend
```

**Commit:** `feat: add stats endpoint with avg price and deal count by city`

---

## Round 6 — Normalize Categories (~80 min in)

**Pause. Say out loud:**

> "Right now categories is comma-separated text — LIKE '%luxury%' is slow and fragile. I need to:
> 1. Create `categories` table (id, name unique)
> 2. Create `deal_categories` association table
> 3. Add M:N relationship on Deal with `secondary`
> 4. Data migration: split text → rows, deduplicate, wire association table, drop text column
> 5. Update list endpoint with `category` filter via JOIN
> 6. Add `selectinload(Deal.categories)` to avoid N+1"

**Delegate to Claude (plan mode)** — full prompt with all 6 steps.

```bash
mise run test:backend && mise run typecheck:backend
```

Verify: `SELECT count(*) FROM categories` → 5, `SELECT count(*) FROM deal_categories` → ~80000.

**Update CLAUDE.md** with query patterns (selectinload for 1:N and M:N, joinedload for N:1).

**Commit:** `feat: normalize categories into M:N with data migration`

---

## Round 7 — Performance Discussion (~85 min in)

**Say out loud:**
> "I wouldn't guess — I'd measure. Three things to check in order:"

1. **Missing indexes** — `EXPLAIN ANALYZE` shows `Seq Scan` → add indexes on WHERE/JOIN/ORDER BY columns
2. **Connection pool exhaustion** — `pg_stat_activity` shows `idle in transaction` → kill sessions, tune pool, PgBouncer
3. **Table bloat** — `pg_stat_user_tables` shows high dead tuple % → `VACUUM ANALYZE`, tune autovacuum

> "Diagnose before optimizing. Adding indexes for a pool problem wastes time."

---

## Phase 3: Show Version History (last 2 min)

```bash
git log --oneline
```

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

# Python REPL (preloads pd and db)
mise run python

# Verify data
psql -h localhost -U super -d super
```

---

## SQL to Memorize

```sql
SELECT count(*) FROM hotels;   -- → 150
SELECT count(*) FROM deals;    -- → 50000

SELECT h.name, h.city, d.room_type, d.price_per_night
FROM deals d JOIN hotels h ON d.hotel_id = h.id LIMIT 3;

SELECT indexname, indexdef FROM pg_indexes
WHERE tablename IN ('hotels','deals') AND indexname NOT LIKE 'pk_%';

-- After normalization
SELECT count(*) FROM categories;        -- → 5
SELECT count(*) FROM deal_categories;   -- → ~80000

-- Performance debugging
EXPLAIN ANALYZE SELECT ... ;
SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'super' GROUP BY state;
SELECT relname, n_live_tup, n_dead_tup FROM pg_stat_user_tables;
```

---

## Interview Loop (every feature from Step 4 onward)

1. **PAUSE** — hands off keyboard, 15–30 seconds
2. **SAY ALOUD** — what changes, which layers, AI or manual
3. **BUILD** — prompt Claude or write it yourself
4. **TEST** — `mise run test:backend && mise run typecheck:backend` + Swagger UI
5. **REVIEW** — read generated code aloud
6. **COMMIT**
