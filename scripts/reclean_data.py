"""DB의 기존 판례 데이터를 clean_html_text로 재정규화하는 스크립트."""

import asyncio
import logging
import sqlite3
from pathlib import Path

# PYTHONPATH 설정 없이 실행 가능하도록 경로 추가
import sys
sys.path.append('src')

from law.config import DB_PATH
from law.utils.text import clean_html_text

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

async def reclean_precedents():
    if not DB_PATH.exists():
        logger.error(f"DB 파일을 찾을 수 없습니다: {DB_PATH}")
        return

    # aiosqlite 대신 단순 처리를 위해 sqlite3 사용
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, holding, summary, full_text FROM precedents")
        rows = cursor.fetchall()
        logger.info(f"총 {len(rows)}건의 판례 데이터를 분석합니다...")

        updated_count = 0
        for row in rows:
            orig_holding = row["holding"] or ""
            orig_summary = row["summary"] or ""
            orig_full_text = row["full_text"] or ""

            # 정규화 적용
            new_holding = clean_html_text(orig_holding)
            new_summary = clean_html_text(orig_summary)
            new_full_text = clean_html_text(orig_full_text)

            if new_holding != orig_holding or new_summary != orig_summary or new_full_text != orig_full_text:
                cursor.execute(
                    "UPDATE precedents SET holding = ?, summary = ?, full_text = ? WHERE id = ?",
                    (new_holding, new_summary, new_full_text, row["id"])
                )
                updated_count += 1

        conn.commit()
        logger.info(f"성공적으로 {updated_count}건의 판례 문단을 정규화(Flowing) 하였습니다.")
        logger.info("이제 TUI(app.py) 또는 export 스크립트를 통해 다시 번들 파일을 생성해 주세요.")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(reclean_precedents())
