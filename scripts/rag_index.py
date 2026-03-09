import asyncio
import logging
import sys
from pathlib import Path

# Fix path to import from src
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from law.db.repository import Repository
from law.db.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rag_index")

async def index_data():
    repo = Repository()
    await repo.connect()
    vs = VectorStore()
    
    # Precedents
    precedents = await repo.fetch_all_precedents()
    logger.info(f"Indexing {len(precedents)} precedents...")
    ids, docs, metas = [], [], []
    for row in precedents:
        text = f"[{row['case_number']}] {row['case_name']}\n"
        if row['holding']: text += f"판시사항: {row['holding']}\n"
        if row['summary']: text += f"요지: {row['summary']}\n"
        if row['full_text']: text += f"본문:\n{row['full_text']}"
        ids.append(f"prec_{row['source_key']}_{row['id']}")
        docs.append(text)
        metas.append({"source": row['source_key'], "type": "precedent", "case_number": row['case_number'], "case_name": row['case_name']})
        if len(ids) >= 100:
            vs.add_documents(ids, docs, metas)
            ids, docs, metas = [], [], []
    if ids: vs.add_documents(ids, docs, metas)

    # Statutes
    statutes = await repo.fetch_all_statutes()
    logger.info(f"Indexing {len(statutes)} statutes...")
    ids, docs, metas = [], [], []
    for row in statutes:
        text = f"[{row['law_name']}] {row['article_number']} {row['article_title']}\n{row['content']}"
        ids.append(f"stat_{row['source_key']}_{row['id']}")
        docs.append(text)
        metas.append({"source": row['source_key'], "type": "statute", "law_name": row['law_name'], "article": row['article_number']})
        if len(ids) >= 100:
            vs.add_documents(ids, docs, metas)
            ids, docs, metas = [], [], []
    if ids: vs.add_documents(ids, docs, metas)

    await repo.close()
    logger.info("RAG indexing completed.")

if __name__ == "__main__":
    asyncio.run(index_data())