import json
from pathlib import Path

import faiss
import numpy as np


class VectorStore:

    def __init__(self, path=None):

        if path is None:
            path = "hr_buddy/data/vector_db"

        self.path = Path(path)

        self.path.mkdir(
            parents=True,
            exist_ok=True
        )

        self.index = None
        self.documents = []
        self.embeddings = []  # Store embeddings in memory to support deletion/update
        self.index_file = self.path / "faiss.index"
        self.docs_file = self.path / "documents.json"
        self.embeddings_file = self.path / "embeddings.npy"

        # Try to load existing index and documents if present
        if self.index_file.exists() and self.docs_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))

                with open(self.docs_file, "r", encoding="utf-8") as fh:
                    self.documents = json.load(fh)

                # Try to load embeddings
                if self.embeddings_file.exists():
                    try:
                        loaded_embeddings = np.load(str(self.embeddings_file))
                        self.embeddings = loaded_embeddings.tolist()
                    except Exception:
                        # If embeddings file is corrupted, reconstruct from index
                        if self.index and self.index.ntotal > 0:
                            self._reconstruct_embeddings_from_index()
                        else:
                            self.embeddings = []
                else:
                    # No embeddings file, try to reconstruct from index
                    if self.index and self.index.ntotal > 0:
                        self._reconstruct_embeddings_from_index()
                    else:
                        self.embeddings = []
            except Exception as e:
                # If loading fails, start fresh
                import traceback
                traceback.print_exc()
                self.index = None
                self.documents = []
                self.embeddings = []

    def build(
        self,
        embeddings,
        documents
    ):

        # Build (replace) index with provided embeddings and documents
        embeddings = np.array(embeddings).astype("float32")

        dimension = embeddings.shape[1]

        # Create a fresh index and overwrite any existing one
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

        # Store embeddings in memory for future deletions/updates
        self.embeddings = embeddings.tolist()

        # Replace documents with provided list
        self.documents = list(documents)

        # Persist to disk
        self._save()

    def add(self, embeddings, documents):
        """Incrementally add embeddings and corresponding documents to the index.

        embeddings: sequence of vectors (n, dim)
        documents: sequence of dicts (length n)
        """
        embeddings = np.array(embeddings).astype("float32")

        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        n, dim = embeddings.shape

        if self.index is None:
            # initialize index with this dimension
            self.index = faiss.IndexFlatIP(dim)

        # Check dimension compatibility
        # Note: IndexFlatIP does not expose dim easily; rely on shape of added vectors
        self.index.add(embeddings)

        # Store embeddings in memory
        self.embeddings.extend(embeddings.tolist())

        # Append documents (must maintain same order as vectors)
        self.documents.extend(list(documents))

        # Persist changes
        self._save()

    def _save(self):
        # Ensure directory exists
        self.path.mkdir(parents=True, exist_ok=True)

        # Write FAISS index
        if self.index is not None:
            try:
                faiss.write_index(self.index, str(self.index_file))
            except Exception:
                # Best-effort; ignore persistence errors here
                pass

        # Write documents
        try:
            with open(self.docs_file, "w", encoding="utf-8") as fh:
                json.dump(self.documents, fh, ensure_ascii=False)
        except Exception:
            pass

        # Write embeddings
        if self.embeddings:
            try:
                embeddings_array = np.array(self.embeddings, dtype=np.float32)
                np.save(str(self.embeddings_file), embeddings_array)
            except Exception:
                pass

    def _get_embeddings_array(self) -> np.ndarray | None:
        """Reconstruct embeddings array from index if possible.

        Note: FAISS IndexFlatIP stores data internally but doesn't expose it easily.
        This method reads from the index if available.
        """
        if self.index is None or self.index.ntotal == 0:
            return None

        try:
            # For IndexFlatIP, we can reconstruct vectors
            n = self.index.ntotal
            d = self.index.d
            embeddings = np.zeros((n, d), dtype=np.float32)
            self.index.reconstruct_n(0, n, embeddings)
            return embeddings
        except Exception:
            return None

    def _reconstruct_embeddings_from_index(self):
        """Reconstruct embeddings list from FAISS index."""
        embeddings = self._get_embeddings_array()
        if embeddings is not None:
            self.embeddings = embeddings.tolist()
        else:
            self.embeddings = []

    def search(
        self,
        embedding,
        top_k=5
    ):

        embedding = np.array(
            [embedding]
        ).astype("float32")

        if self.index is None:
            raise ValueError("Vector store index is not initialized. Please call the build method first.")

        scores, indexes = self.index.search(
            embedding,
            top_k
        )

        results = []

        for score, index in zip(
            scores[0],
            indexes[0]
        ):

            if index == -1:
                continue

            document = self.documents[index]

            results.append(
                {
                    **document,
                    "score": float(score)
                }
            )

        return results

    def get_chunk(self, chunk_id: int) -> dict | None:
        """Get a chunk by its index/ID.

        chunk_id: 0-based index of the chunk
        returns: chunk dict with document name and content, or None if out of range
        """
        if chunk_id < 0 or chunk_id >= len(self.documents):
            return None

        return {
            **self.documents[chunk_id],
            "chunk_id": chunk_id
        }

    def delete_by_document(self, document_name: str):
        """Delete all chunks belonging to a specific document and rebuild index.

        document_name: name of the document to delete all chunks for
        returns: number of chunks deleted
        """
        original_count = len(self.documents)

        # Find indices to delete (in reverse order to avoid index shift)
        indices_to_delete = [
            i for i, doc in enumerate(self.documents)
            if doc.get("document") == document_name
        ]

        # Delete in reverse order to maintain correct indices
        for i in reversed(indices_to_delete):
            self.documents.pop(i)
            if i < len(self.embeddings):
                self.embeddings.pop(i)

        deleted_count = original_count - len(self.documents)

        if deleted_count > 0:
            self._rebuild_index()
            self._save()

        return deleted_count

    def delete_by_index(self, chunk_index: int):
        """Delete a specific chunk by its index and rebuild index.

        chunk_index: 0-based index of the chunk to delete
        returns: True if successful, False if index out of range
        """
        try:
            # Validate index
            if chunk_index < 0 or chunk_index >= len(self.documents):
                return False

            # Ensure embeddings list is properly synced
            if len(self.embeddings) != len(self.documents):
                # Try to reconstruct embeddings if there's a mismatch
                if self.index and self.index.ntotal > 0:
                    self._reconstruct_embeddings_from_index()
                else:
                    # No index to reconstruct from, can't proceed safely
                    return False

            # Delete the document
            self.documents.pop(chunk_index)
            
            # Delete corresponding embedding
            if chunk_index < len(self.embeddings):
                self.embeddings.pop(chunk_index)
            
            # Rebuild and save
            if self.documents and self.embeddings:
                self._rebuild_index()
            else:
                # If nothing left, clear everything
                self.index = None
            
            self._save()
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in delete_by_index({chunk_index}): {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_chunk(self, chunk_index: int, new_embedding, new_document: dict):
        """Update a chunk's embedding and metadata by index and rebuild index.

        chunk_index: 0-based index of the chunk to update
        new_embedding: new vector for this chunk
        new_document: new metadata dict for this chunk
        returns: True if successful, False if index out of range
        """
        if chunk_index < 0 or chunk_index >= len(self.documents):
            return False

        self.documents[chunk_index] = new_document
        self._rebuild_index()
        self._save()

        return True

    def clear(self):
        """Clear all documents and index."""
        self.documents = []
        self.embeddings = []
        self.index = None
        self._save()

    def get_info(self) -> dict:
        """Get information about the current index state."""
        return {
            "num_documents": len(self.documents),
            "num_vectors": self.index.ntotal if self.index else 0,
            "documents_by_name": self._get_document_stats()
        }

    def _get_document_stats(self) -> dict:
        """Count chunks by document name."""
        stats = {}
        for doc in self.documents:
            doc_name = doc.get("document", "unknown")
            stats[doc_name] = stats.get(doc_name, 0) + 1
        return stats

    def _rebuild_index(self):
        """Rebuild FAISS index from current documents and embeddings.

        Used after deletions or updates. Reconstructs the index from stored embeddings.
        """
        try:
            if not self.documents or not self.embeddings:
                self.index = None
                return

            # Make sure counts match
            if len(self.embeddings) != len(self.documents):
                # Mismatch - can't proceed
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Embedding/document count mismatch: {len(self.embeddings)} vs {len(self.documents)}")
                self.index = None
                return

            # Rebuild index from stored embeddings
            embeddings_array = np.array(self.embeddings, dtype=np.float32)
            if embeddings_array.size == 0:
                self.index = None
                return
                
            d = embeddings_array.shape[1]
            self.index = faiss.IndexFlatIP(d)
            self.index.add(embeddings_array)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error rebuilding index: {e}")
            import traceback
            traceback.print_exc()
            self.index = None