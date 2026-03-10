import pytest
from law.db.vector_store import VectorStore
from law.db.repository import Repository

@pytest.mark.asyncio
async def test_rag_search_consistency(repo: Repository):
    vs = VectorStore()
    
    # 1. 원본 데이터 하나 샘플링 (판례 예시)
    precedents = await repo.fetch_all_precedents()
    if not precedents:
        pytest.skip("No precedents in DB to test RAG quality.")
        
    sample = precedents[0]
    db_key = repo.route_source(sample["source_key"])
    expected_id = f"{db_key}_precedents_{sample['id']}"
    
    # 2. 해당 ID로 검색 (Top-K 내 포함 여부 확인)
    query_text = (sample["case_name"] or "") + " " + (sample["case_number"] or "")
    results = vs.search(query_text, n_results=5)
    
    # QueryResult 규격: results["ids"][0]에 결과 ID 리스트가 들어있음
    found_ids = results.get("ids", [[]])[0]
    assert expected_id in found_ids, f"Expected ID {expected_id} not found in search results for query '{query_text}'"
    
    # 3. 메타데이터 정합성 확인
    idx = found_ids.index(expected_id)
    metadatas = results.get("metadatas", [[]])[0]
    target_meta = metadatas[idx]
    
    assert target_meta["source"] == sample["source_key"]
    assert target_meta["db_key"] == db_key

@pytest.mark.asyncio
async def test_rag_statute_indexing(repo: Repository):
    vs = VectorStore()
    statutes = await repo.fetch_all_statutes()
    if not statutes:
        pytest.skip("No statutes in DB to test RAG quality.")
        
    sample = statutes[0]
    expected_id = f"statutes_statutes_{sample['id']}"
    
    results = vs.search(sample["law_name"] + " " + sample["article_number"], n_results=10)
    found_ids = results.get("ids", [[]])[0]
    assert expected_id in found_ids