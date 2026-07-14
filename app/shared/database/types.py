from sqlalchemy import BigInteger, Integer

# PostgreSQL uses BIGINT identifiers throughout the migration history. The
# SQLite variant preserves implicit row-id generation in focused unit tests.
BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")
