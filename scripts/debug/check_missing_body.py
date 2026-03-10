import asyncio
import aiosqlite
from pathlib import Path

async def check():
    db_path = Path('c:/develop/law/data/law_precedents.db')
    if not db_path.exists():
        print(f'DB not found at {db_path}')
        return
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute('SELECT source_key, case_name, case_number FROM precedents WHERE full_text IS NULL AND summary IS NULL') as cursor:
            rows = await cursor.fetchall()
            print(f'Found {len(rows)} problematic rows:')
            for row in rows:
                print(f'PROBLEM: {row["source_key"]} - {row["case_number"]} - {row["case_name"]}')

if __name__ == "__main__":
    asyncio.run(check())