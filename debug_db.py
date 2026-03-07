import asyncio
import aiosqlite
from pathlib import Path

async def check_db():
    db_path = Path("data/law.db")
    if not db_path.exists():
        print("DB not found.")
        return

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        # Check statutes
        async with db.execute("SELECT source_key, article_number, article_title, length(content) as content_len FROM statutes LIMIT 5") as cursor:
            print("\n--- Statutes ---")
            rows = await cursor.fetchall()
            for row in rows:
                print(f"[{row['source_key']}] {row['article_number']}({row['article_title']}) - {row['content_len']} chars")

        # Check a sample content
        async with db.execute("SELECT content FROM statutes LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                print("\n- Sample Content (Statute) -")
                print(row['content'][:500] + "...")

        # Check precedents
        async with db.execute("SELECT source_key, case_number, length(full_text) as full_text_len FROM precedents LIMIT 5") as cursor:
            print("\n--- Precedents ---")
            rows = await cursor.fetchall()
            for row in rows:
                print(f"[{row['source_key']}] {row['case_number']} - {row['full_text_len']} chars")

        # Check a sample content
        async with db.execute("SELECT full_text FROM precedents LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                print("\n- Sample Content (Precedent) -")
                print(row['full_text'][:500] + "...")

if __name__ == "__main__":
    asyncio.run(check_db())
