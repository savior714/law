import logging
import chromadb
from chromadb.utils import embedding_functions
from law.config import CHROMA_PATH, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class VectorStore:
    """Wrapper for ChromaDB with multilingual embedding support."""

    def __init__(self, collection_name: str = "law_precedents"):
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        
        # Use SentenceTransformer embedding function with the multilingual model from config
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, ids: list[str], documents: list[str], metadatas: list[dict]):
        """Add or update documents in the vector store."""
        try:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Successfully indexed {len(ids)} documents into '{self.collection.name}'.")
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            raise

    def search(self, query_text: str, n_results: int = 5):
        """Search for similar documents."""
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

    def reset(self):
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