import asyncio
import aiosqlite
import json

async def check():
    async with aiosqlite.connect("data/law.db") as db:
        db.row_factory = aiosqlite.Row
        # check table columns
        async with db.execute("PRAGMA table_info(statutes)") as cursor:
            cols = await cursor.fetchall()
            print("Statutes Columns:")
            for col in cols:
                print(f" - {col['name']} ({col['type']})")

        async with db.execute("PRAGMA table_info(admin_rules)") as cursor:
            cols = await cursor.fetchall()
            print("\nAdmin Rules Columns:")
            for col in cols:
                print(f" - {col['name']} ({col['type']})")

if __name__ == "__main__":
    asyncio.run(check())
