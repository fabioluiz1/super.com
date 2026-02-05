# Database Configuration

## Connection Pool

SQLAlchemy maintains a pool of database connections that are reused across requests. This avoids the overhead of establishing a new connection for every query.

### Pool Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `pool_size` | 5 | Number of persistent connections kept open. These connections are always available, even when idle. |
| `max_overflow` | 10 | Extra connections created under load, beyond `pool_size`. These are closed when no longer needed. Total max = `pool_size + max_overflow`. |
| `pool_timeout` | 30 | Seconds to wait for an available connection before raising `TimeoutError`. If all connections are busy and max_overflow is reached, new requests wait up to this long. |
| `pool_recycle` | 3600 | Recreate connections older than this (seconds). Prevents issues with stale connections that databases may close after inactivity. Set lower than your database's `wait_timeout`. |
| `pool_pre_ping` | true | Test each connection with `SELECT 1` before checkout. Catches dead connections (network issues, database restart) before your query fails. Small overhead (~1ms) but prevents cryptic errors. |
| `echo` | false | Log all SQL statements. Enable for debugging, disable in production (noisy and potential security risk). |
| `statement_timeout` | 30 | Max seconds a query can run before being killed. Prevents runaway queries from holding connections and blocking other requests. |

### Tuning for Production

**Sizing `pool_size`**: Start with `pool_size = number_of_web_workers`. Each worker needs at least one connection. If your app makes concurrent database calls within a single request (e.g., parallel queries), increase accordingly.

**Sizing `max_overflow`**: This handles traffic spikes. Set it high enough to absorb bursts without queuing requests. Monitor for `TimeoutError` exceptions — if you see them, increase `max_overflow` or `pool_size`.

**`pool_recycle` and cloud databases**: AWS RDS, Cloud SQL, and other managed databases often close idle connections after 5-10 minutes. Set `pool_recycle` lower than their timeout (e.g., 300 seconds for a 10-minute database timeout).

### Environment Variables

Configure via environment variables (see `.env.example`):

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_ECHO=false
DB_STATEMENT_TIMEOUT=30
```

## Naming Conventions

SQLAlchemy uses naming conventions to generate consistent constraint names. This is critical for Alembic migrations — without predictable names, Alembic can't generate `DROP CONSTRAINT` statements correctly.

The conventions follow this pattern:

| Constraint | Pattern | Example |
|------------|---------|---------|
| Primary key | `pk_%(table_name)s` | `pk_users` |
| Foreign key | `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s` | `fk_orders_user_id_users` |
| Unique | `uq_%(table_name)s_%(column_0_name)s` | `uq_users_email` |
| Check | `ck_%(table_name)s_%(constraint_name)s` | `ck_orders_amount_positive` |
| Index | `ix_%(column_0_label)s` | `ix_users_email` |

This is equivalent to Rails' automatic constraint naming — you never need to manually name constraints, and migrations work correctly.
