from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Neon URLs usually look like: postgresql://user:pass@ep-flat-water-123.us-east-2.aws.neon.tech/neondb
# asyncpg requires postgresql+asyncpg://
db_url = settings.DATABASE_URL
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Remove channel_binding if present as it can cause issues with some drivers
if "channel_binding" in db_url:
    import re
    db_url = re.sub(r'([?&])channel_binding=[^&]*', r'\1', db_url).rstrip('?&')

# Neon often requires SSL
# If sslmode is already in the URL, asyncpg will use it. 
# Otherwise, we force it for neon.tech domains.
engine_args = {
    "echo": False,
    "future": True,
    "pool_size": 10,
    "max_overflow": 20,
}

if db_url and "neon.tech" in db_url and "sslmode" not in db_url:
    engine_args["connect_args"] = {"ssl": "require"}

engine = create_async_engine(db_url if db_url else "sqlite+aiosqlite:///:memory:", **engine_args)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
