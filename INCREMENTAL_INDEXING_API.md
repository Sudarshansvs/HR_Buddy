# Incremental Indexing API Reference

This document describes the API endpoints for managing the FAISS vector store with incremental add, update, delete, and clear operations.

## Endpoints

### 1. Add Chunks (Incremental)
**POST** `/api/v1/documents/add-chunks`

Add pre-chunked documents to the index without rebuilding the entire index.

**Request Body:**
```json
[
  {
    "document": "handbook",
    "content": "New HR policy text here"
  },
  {
    "document": "handbook", 
    "content": "More policy content"
  }
]
```

**Response:**
```json
{
  "message": "Added 2 chunks to index"
}
```

### 2. Delete Document
**DELETE** `/api/v1/documents/by-document`

Delete all chunks belonging to a specific document.

**Query Parameters:**
- `document_name` (required): Name of the document to delete

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/by-document?document_name=handbook"
```

**Response:**
```json
{
  "message": "Deleted 42 chunks for document 'handbook'",
  "deleted_count": 42
}
```

### 3. Update Chunk
**PUT** `/api/v1/documents/chunk`

Update a specific chunk's content and re-embed it.

**Request Body:**
```json
{
  "chunk_index": 5,
  "new_text": "Updated content for this chunk",
  "document_name": "handbook"
}
```

**Response:**
```json
{
  "message": "Updated chunk 5",
  "success": true
}
```

### 4. Clear Index
**POST** `/api/v1/documents/clear`

Remove all documents and chunks from the index.

**Response:**
```json
{
  "message": "Index cleared successfully"
}
```

### 5. Get Index Info
**GET** `/api/v1/documents/info`

Get statistics about the current index state.

**Response:**
```json
{
  "num_documents": 127,
  "num_vectors": 127,
  "documents_by_name": {
    "handbook": 45,
    "policy": 32,
    "onboarding": 50
  }
}
```

### 6. Reload Documents
**POST** `/api/v1/documents/reload`

Rebuild the in-memory retrieval index from documents on disk. Replaces the entire index.

**Response:**
```json
{
  "message": "Document index reloaded"
}
```

### 7. Upload Document
**POST** `/api/v1/documents/upload`

Upload a new document, save it to the documents folder, and re-index. Supports .txt, .md, and .pdf files.

**Request:** `multipart/form-data` with file upload

**Response:**
```json
{
  "filename": "newfile.txt",
  "preview": "First 1000 characters of the file...",
  "message": "Uploaded and indexed"
}
```

## Implementation Details

### Persistence
- FAISS index: `hr_buddy/data/vector_db/faiss.index`
- Documents metadata: `hr_buddy/data/vector_db/documents.json`
- Automatically saved after every add, delete, update, or clear operation

### Incremental Adds vs Full Rebuild
- **Incremental Add** (`POST /add-chunks`): Appends new vectors to the index without reprocessing existing documents. Fast for adding documents one at a time.
- **Full Rebuild** (`POST /reload`): Reprocesses all documents from disk and rebuilds the entire index from scratch. Use when you want a clean state.

### Constraints
- Delete and update operations internally rebuild the FAISS index by extracting and reorganizing vectors
- Updating a chunk requires re-embedding the new text
- Delete operations preserve vector order by filtering documents and reconstructing the index

## Examples

### Add new HR content incrementally
```bash
curl -X POST http://localhost:8000/api/v1/documents/add-chunks \
  -H "Content-Type: application/json" \
  -d '[
    {"document": "benefits_2024", "content": "New benefits policy text"},
    {"document": "benefits_2024", "content": "Additional benefits information"}
  ]'
```

### Check current index status
```bash
curl http://localhost:8000/api/v1/documents/info
```

### Delete outdated document
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/by-document?document_name=old_policy"
```

### Update a specific chunk
```bash
curl -X PUT http://localhost:8000/api/v1/documents/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_index": 10,
    "new_text": "Updated policy text",
    "document_name": "handbook"
  }'
```

### Clear all indexed data
```bash
curl -X POST http://localhost:8000/api/v1/documents/clear
```

## Performance Considerations

- **Incremental add**: O(n) where n is number of vectors being added. Very fast.
- **Delete by document**: O(m*d) where m is number of documents, d is embedding dimension. Rebuilds entire index.
- **Update chunk**: O(m*d). Rebuilds entire index.
- **Clear**: O(1). Just clears memory and files.

For frequent deletes/updates with large indices, consider batching operations before applying them.
