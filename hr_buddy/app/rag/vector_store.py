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

    def build(
        self,
        embeddings,
        documents
    ):

        embeddings = np.array(
            embeddings
        ).astype("float32")

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(
            dimension
        )

        self.index.add(
            embeddings
        )

        self.documents = documents

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