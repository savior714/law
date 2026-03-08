import asyncio
import aiosqlite

async def check_inspect():
    async with aiosqlite.connect("data/law.db") as db:
        db.row_factory = aiosqlite.Row
        # Get Article 1 of any source
        async with db.execute("SELECT content FROM statutes WHERE article_number = '제1조' LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                print("\n--- Article 1 Content Raw ---")
                print(row['content'])
                print("----------------------------\n")

if __name__ == "__main__":
    asyncio.run(check_inspect())
