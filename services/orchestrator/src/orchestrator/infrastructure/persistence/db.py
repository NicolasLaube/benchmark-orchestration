import os

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

DATABASE_URL = os.environ["DATABASE_URL"]


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)


# Session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_session():
    async with SessionLocal() as session:
        yield session
