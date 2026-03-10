import logging
from typing import Mapping, Sequence, Union, Optional, cast, TypedDict

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from law.config import CHROMA_PATH, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Metadata values can be string, integer, float, or boolean in ChromaDB.
MetadataValue = Union[str, int, float, bool]
MetadataType = Mapping[str, MetadataValue]

class QueryResult(TypedDict, total=False):
    """Refined type for search results."""
    ids: list[list[str]]
    distances: Optional[list[list[float]]]
    metadatas: Optional[list[list[Optional[MetadataType]]]]
    embeddings: Optional[list[list[list[float]]]]
    documents: Optional[list[list[str]]]
    uris: Optional[list[list[str]]]
    data: Optional[list[list[str]]]

class VectorStore:
    """Wrapper for ChromaDB with multilingual embedding support."""

    def __init__(self, collection_name: str = "law_precedents") -> None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        
        # Use SentenceTransformer embedding function with the multilingual model from config
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        
        self.collection: Collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, ids: Sequence[str], documents: Sequence[str], metadatas: Sequence[MetadataType]) -> None:
        """Add or update documents in the vector store."""
        try:
            # According to chromadb documentation, metadatas should be a list of maps.
            # Using cast with a specific type list[dict[str, MetadataValue]] to satisfy type checker.
            self.collection.upsert(
                ids=list(ids),
                documents=list(documents),
                metadatas=cast(list[dict[str, Union[str, int, float, bool]]], list(metadatas))
            )
            logger.info(f"Successfully indexed {len(ids)} documents into '{self.collection.name}'.")
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            raise

    def search(self, query_text: str, n_results: int = 5) -> QueryResult:
        """Search for similar documents. Returns QueryResult object."""
        res = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return cast(QueryResult, res)

    def reset(self) -> None:
        """Delete and recreate the collection."""
        try:
            name = self.collection.name
            self.client.delete_collection(name)
            self.collection = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.ef,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Collection '{name}' reset.")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")