#!/usr/bin/env python3
"""Quick test of delete_by_index functionality."""

import sys
sys.path.insert(0, '/Users/sudarshanseshabattar/Documents/HR_Buddy')

import numpy as np
from hr_buddy.app.rag.vector_store import VectorStore

# Create a test vector store
vs = VectorStore(path="/tmp/test_vector_db")

# Add some test data
embeddings = np.random.rand(5, 384).astype(np.float32)  # 5 vectors, 384 dims
documents = [
    {"document": "doc1", "content": f"chunk {i}"}
    for i in range(5)
]

print("Building index with 5 chunks...")
vs.build(embeddings, documents)
print(f"Index info: {vs.get_info()}")

# Try to get a chunk
print(f"\nGetting chunk 2: {vs.get_chunk(2)}")

# Try to delete a chunk
print(f"\nDeleting chunk 2...")
success = vs.delete_by_index(2)
print(f"Delete success: {success}")

# Check index after delete
print(f"Index info after delete: {vs.get_info()}")

# Verify chunk 2 is gone
print(f"Getting chunk 2 again (should be different or None): {vs.get_chunk(2)}")

print("\nTest completed successfully!")
