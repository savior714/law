import asyncio
import sys
from pathlib import Path

# Fix path to import from src
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "src"))

from law.db.repository import Repository
from law.db.vector_store import VectorStore

async def verify():
    repo = Repository()
    await repo.connect()
    
    # SQLite counts
    cnt_statutes = await repo.count_records("statutes")
    cnt_admin_rules = await repo.count_records("admin_rules")
    cnt_precedents = await repo.count_records("precedents")
    total_sql = cnt_statutes + cnt_admin_rules + cnt_precedents
    
    # Vector store counts
    vs = VectorStore()
    cnt_vector = vs.collection.count()
    
    print("--- RAG Integration Verification ---")
    print(f"SQLite Records (Total): {total_sql}")
    print(f"  - Statutes: {cnt_statutes}")
    print(f"  - Admin Rules: {cnt_admin_rules}")
    print(f"  - Precedents: {cnt_precedents}")
    print(f"Vector Store Count: {cnt_vector}")
    
    if total_sql == cnt_vector:
        print("\n[SUCCESS] SQLite and Vector Store counts match!")
    else:
        print(f"\n[WARNING] Count mismatch: SQL={total_sql} vs Vector={cnt_vector}")
        print("Note: This might be due to empty/short documents being skipped during indexing.")

    # Simple Search Test
    query = "음주운전"
    print(f"\n--- Testing Search: `'{query}'` ---")
    results = vs.search(query, n_results=3)
    
    if results and results.get("ids") and results["ids"][0]:
        for i, (doc_id, dist) in enumerate(zip(results["ids"][0], results["distances"][0])):
            meta = results["metadatas"][0][i]
            print(f"{i+1}. [{doc_id}] Dist: {dist:.4f}")
            print(f"   Meta: {meta}")
    else:
        print("No results found.")

    await repo.close()

if __name__ == "__main__":
    asyncio.run(verify())
