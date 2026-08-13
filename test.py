import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine(
        "sqlite+aiosqlite:///./facturemoi.db",
        echo=True
    )

    async with engine.begin() as conn:
        print("OK")

asyncio.run(main())