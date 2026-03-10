import asyncio
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Union

from tqdm import tqdm

# Fix path to import from src
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from law.db.repository import Repository, ShardKey, TableName
from law.db.vector_store import VectorStore, MetadataType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("rag_index")

async def index_data(force_all: bool = False):
    """SQLite 데이터를 ChromaDB 벡터 스토어로 이관 및 인덱싱 (증분 방식 지원)."""
    repo = Repository()
    await repo.connect()
    vs = VectorStore()
    
    # 1. 동기화 시점 확인
    last_sync = "1970-01-01T00:00:00Z"
    if not force_all:
        last_sync = await repo.get_last_sync_at()
        logger.info(f"Incremental sync: processing records scraped after {last_sync}")
    else:
        logger.info("Force-all index: processing all records from scratch.")
    
    batch_size = 200
    new_sync_timestamp = datetime.now(timezone.utc).isoformat()
    
    def upsert_batch(ids, docs, metas):
        if ids:
            try:
                vs.add_documents(ids, docs, metas)
            except Exception as e:
                logger.error(f"Batch upsert failed: {e}")

    # --- 1. Precedents (판례/결정례) ---
    logger.info("Fetching precedents...")
    precedents = await repo.fetch_all_precedents(since=last_sync)
    if precedents:
        logger.info(f"Indexing {len(precedents)} new precedents...")
        ids, docs, metas = [], [], []
        for row in tqdm(precedents, desc="Precedents"):
            try:
                db_key = repo.route_source(row["source_key"])
                table: TableName = "precedents"
                comp_id = f"{db_key}_{table}_{row['id']}"
                
                text = f"[{row['case_number']}] {row['case_name'] or ''}\n"
                if row["holding"]: text += f"판시사항: {row['holding']}\n"
                if row["summary"]: text += f"요지: {row['summary']}\n"
                if row["full_text"]: text += f"본문:\n{row['full_text']}"
                
                if not text.strip() or len(text) < 10:
                    continue
                    
                ids.append(comp_id)
                docs.append(text)
                metas.append({
                    "source": row["source_key"],
                    "db_key": db_key,
                    "table": table,
                    "type": "precedent",
                    "case_number": row["case_number"],
                    "case_name": row["case_name"] or ""
                })
                
                if len(ids) >= batch_size:
                    upsert_batch(ids, docs, metas)
                    ids, docs, metas = [], [], []
            except Exception as e:
                logger.error(f"Error processing precedent {row.get('id', 'unknown')}: {e}")
        upsert_batch(ids, docs, metas)
    else:
        logger.info("No new precedents found.")

    # --- 2. Statutes (법령) ---
    logger.info("Fetching statutes...")
    statutes = await repo.fetch_all_statutes(since=last_sync)
    if statutes:
        logger.info(f"Indexing {len(statutes)} new statutes...")
        ids, docs, metas = [], [], []
        for row in tqdm(statutes, desc="Statutes"):
            try:
                db_key = "statutes"
                table: TableName = "statutes"
                comp_id = f"{db_key}_{table}_{row['id']}"
                text = f"[{row['law_name']}] {row['article_number']} {row['article_title'] or ''}\n{row['content']}"
                
                ids.append(comp_id)
                docs.append(text)
                metas.append({
                    "source": row["source_key"],
                    "db_key": db_key,
                    "table": table,
                    "type": "statute",
                    "law_name": row["law_name"],
                    "article": row["article_number"]
                })
                
                if len(ids) >= batch_size:
                    upsert_batch(ids, docs, metas)
                    ids, docs, metas = [], [], []
            except Exception as e:
                logger.error(f"Error processing statute {row.get('id', 'unknown')}: {e}")
        upsert_batch(ids, docs, metas)
    else:
        logger.info("No new statutes found.")

    # --- 3. Admin Rules (행정규칙) ---
    logger.info("Fetching admin rules...")
    rules = await repo.fetch_all_admin_rules(since=last_sync)
    if rules:
        logger.info(f"Indexing {len(rules)} new admin rules...")
        ids, docs, metas = [], [], []
        for row in tqdm(rules, desc="AdminRules"):
            try:
                db_key = "statutes"
                table: TableName = "admin_rules"
                comp_id = f"{db_key}_{table}_{row['id']}"
                text = f"[{row['rule_name']}] {row['article_number']} {row['article_title'] or ''}\n{row['content']}"
                
                ids.append(comp_id)
                docs.append(text)
                metas.append({
                    "source": row["source_key"],
                    "db_key": db_key,
                    "table": table,
                    "type": "admin_rule",
                    "rule_name": row["rule_name"],
                    "article": row["article_number"]
                })
                
                if len(ids) >= batch_size:
                    upsert_batch(ids, docs, metas)
                    ids, docs, metas = [], [], []
            except Exception as e:
                logger.error(f"Error processing admin rule {row.get('id', 'unknown')}: {e}")
        upsert_batch(ids, docs, metas)
    else:
        logger.info("No new admin rules found.")

    # 동기화 시점 업데이트
    await repo.update_sync_at("chromadb", new_sync_timestamp)
    await repo.close()
    logger.info(f"RAG indexing completed. last_sync_at updated to {new_sync_timestamp}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index legal data into ChromaDB.")
    parser.add_argument("--force", action="store_true", help="Index all records from scratch.")
    args = parser.parse_args()
    
    asyncio.run(index_data(force_all=args.force))