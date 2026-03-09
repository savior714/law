import asyncio
from law.db.schema import init_db
from law.config import DB_PATHS
import os

async def main():
    print("Initializing sharded databases...")
    await init_db()
    
    for key, path in DB_PATHS.items():
        if os.path.exists(path):
            print(f"✅ Created: {key} -> {path}")
        else:
            print(f"❌ Failed: {key} -> {path}")

if __name__ == "__main__":
    asyncio.run(main())
