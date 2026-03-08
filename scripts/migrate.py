import asyncio
from law.db.schema import init_db

async def migrate():
    print("Migrating database...")
    await init_db()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(migrate())
