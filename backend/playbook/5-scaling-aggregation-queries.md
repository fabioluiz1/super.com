# Scaling Aggregation Queries — Dashboard Performance

When the interviewer asks about the stats endpoint getting slow, or when you proactively mention performance during Round 4.

---

## The core question to ask first

> "Does this dashboard data need to be real-time, or is it OK to be stale for a period — minutes, hours, a day?"

This determines everything. Hotel deal stats (average prices, deal counts by city) don't change every second. If the data is updated hourly or daily, caching the query result eliminates the problem entirely — no query optimization needed.

If thousands of users open the dashboard and each one fires a `GROUP BY` aggregation over millions of rows with JOINs, that's a real bottleneck — not because one query is slow, but because hundreds of identical expensive queries run concurrently.

## Performance ladder — try in this order

Each step is more expensive and complex than the previous. Only escalate when the previous step isn't enough.

### 1. Indexes (cost: zero, complexity: low)

Always the first thing to check. Free performance — no infrastructure, no code changes beyond a migration.

```sql
CREATE INDEX ix_hotels_city ON hotels (city);
CREATE INDEX ix_deals_hotel_id ON deals (hotel_id);
CREATE INDEX ix_deals_is_available ON deals (is_available);
```

- `GROUP BY hotels.city` → index scan instead of sequential scan
- `JOIN deals ON hotel_id` → index nested loop join instead of hash join
- `WHERE is_available = true` → skips unavailable rows via index

**When it's not enough**: indexes speed up individual queries but don't help when 1,000 users fire the same expensive aggregation concurrently.

### 2. Application-level cache (cost: low, complexity: low–medium)

Cache the query result in memory or Redis with a TTL. Every request within the TTL window gets the cached result — one query serves thousands of users.

```python
# Concept — cache the stats response
@router.get("/deals/stats")
async def get_stats(db: DB):
    cached = await redis.get("deals:stats")
    if cached:
        return json.loads(cached)

    stats = await deal_repository.get_stats(db)
    await redis.setex("deals:stats", 300, json.dumps(stats))  # 5-min TTL
    return stats
```

**TTL strategies by use case**:

| Data freshness | TTL | Example |
|---|---|---|
| Near real-time | 30–60 seconds | Stock prices, live inventory |
| Minutes stale OK | 5–15 minutes | Dashboard stats, search counts |
| Hours stale OK | 1–6 hours | Analytics, reports |
| Daily refresh OK | 24 hours or cron job | Leaderboards, daily digests |

For hotel deal stats, **5–15 minutes** is the sweet spot. Deals don't change every second, and users won't notice a 5-minute lag.

**Cache invalidation**: for simple TTL-based caching, there's nothing to invalidate — the cache expires naturally. For more complex scenarios (cache must update when deals change), invalidate on write: when a deal is created/updated/deleted, delete the cache key. This is the simplest form of what Rails calls "Russian doll caching" — nested cache layers where inner caches (per-city stats) are invalidated independently of outer caches (full dashboard).

**When it's not enough**: if different users need different filtered views (stats for city X, stats for available-only), the cache key space explodes. At that point, consider materialized views.

### 3. Materialized views (cost: low, complexity: medium)

A materialized view is a precomputed table that stores the result of a query. PostgreSQL creates it once, and you refresh it on a schedule.

```sql
CREATE MATERIALIZED VIEW deal_stats_by_city AS
SELECT h.city, AVG(d.price_per_night) AS avg_price, COUNT(*) AS deal_count
FROM deals d
JOIN hotels h ON d.hotel_id = h.id
WHERE d.is_available = true
GROUP BY h.city;

-- Refresh periodically (cron job or pg_cron)
REFRESH MATERIALIZED VIEW CONCURRENTLY deal_stats_by_city;
```

- Queries against the view are instant — it's just a table scan on precomputed rows
- `CONCURRENTLY` allows reads during refresh (requires a unique index on the view)
- No application code changes — the repository just queries the view instead of the base tables
- **Trade-off**: data is stale between refreshes. You control the refresh interval (cron every 5 min, hourly, etc.)

**When it's not enough**: if you need real-time aggregations or the dataset is so large that even the refresh takes too long.

### 4. Read replicas (cost: medium, complexity: medium)

Route read-heavy queries (dashboards, reports, search) to a read replica. The primary handles writes.

```
Primary DB (writes) ──replication──▶ Read Replica (reads)
      │                                    │
  deal creation                     GET /deals/stats
  deal updates                      GET /deals?city=Toronto
```

- Managed Postgres (AWS RDS, GCP Cloud SQL) makes this a checkbox — no manual replication setup
- Application needs a second connection pool pointed at the replica
- **Trade-off**: replication lag (typically <1 second for async replication, but can spike under load). Dashboard queries might see slightly stale data.
- **Cost**: doubles your database bill. A `db.r6g.xlarge` on RDS is ~$400/month — a replica doubles that.

**When it's not enough**: if the table is so large that even on a replica, the aggregation is slow (billions of rows).

### 5. Table partitioning (cost: low, complexity: high)

Split a large table into smaller physical partitions. PostgreSQL routes queries to the relevant partition(s) automatically.

```sql
-- Partition deals by checkin_date (range partitioning)
CREATE TABLE deals (
    id SERIAL,
    hotel_id INT,
    checkin_date DATE,
    ...
) PARTITION BY RANGE (checkin_date);

CREATE TABLE deals_2025_q1 PARTITION OF deals FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
CREATE TABLE deals_2025_q2 PARTITION OF deals FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');
```

- A query for `WHERE checkin_date BETWEEN '2025-01-01' AND '2025-03-31'` only scans `deals_2025_q1` — skips all other partitions (partition pruning)
- **Trade-off**: complex to set up and maintain. Partition key choice is critical — wrong key means queries still scan all partitions. Cross-partition queries (no filter on the partition key) are slower than unpartitioned tables.
- Best for time-series data, audit logs, or tables with a natural date-based partition key

**When it's not enough**: if your bottleneck isn't scan size but concurrent query volume (then caching or read replicas help more).

## Summary table

| Step | Helps with | Cost | Complexity | Data freshness |
|---|---|---|---|---|
| **Indexes** | Slow individual queries | Free | Migration only | Real-time |
| **App cache (Redis)** | Concurrent identical queries | ~$15/month (ElastiCache) | Low | TTL-based (seconds–hours) |
| **Materialized view** | Expensive aggregations | Free (built into Postgres) | Medium | Refresh interval |
| **Read replica** | Read-heavy load on primary | ~$400/month (doubles DB) | Medium | Replication lag (<1s typical) |
| **Partitioning** | Huge tables (billions of rows) | Free (built into Postgres) | High | Real-time |

## What to say in the interview

> "The first question is whether this data needs to be real-time. Dashboard stats for hotel deals probably don't — if it's 5 minutes stale, nobody notices. So before optimizing the query itself, I'd cache the result in Redis with a 5-minute TTL. One query serves thousands of users.
>
> If we still need to optimize the query: indexes first — they're free. Then a materialized view if the aggregation itself is too expensive. Read replicas if the problem is concurrent load, not query speed. Partitioning only if the table has billions of rows with a natural partition key like date.
>
> The key insight is that each step has a cost — both in money and complexity. Indexes are free. A Redis cache is $15/month. A read replica doubles your database bill. You only escalate when the previous step isn't enough, and you need production metrics to decide which step to take."
