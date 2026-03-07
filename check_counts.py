
import asyncio
from law.db.repository import Repository

async def check():
    repo = Repository()
    try:
        await repo.connect()
        s_count = await repo.count_records("statutes")
        a_count = await repo.count_records("admin_rules")
        print(f"Statutes count: {s_count}")
        print(f"AdminRules count: {a_count}")
    finally:
        await repo.close()

if __name__ == "__main__":
    asyncio.run(check())
