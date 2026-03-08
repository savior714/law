"""Export the dataset to bundles."""

import asyncio
import logging
import sys
sys.path.append('src')

from law.db.repository import Repository
from law.export.builder import build_dataset

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

async def run_export():
    repo = Repository()
    try:
        await repo.connect()
        counts = await build_dataset(repo)
        logger.info(f"수출이 완료되었습니다: {counts}")
        logger.info("data/export/ 폴더의 BUNDLE 파일을 확인해 주세요.")
    finally:
        await repo.close()

if __name__ == "__main__":
    asyncio.run(run_export())
