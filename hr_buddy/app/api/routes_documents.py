from pathlib import Path
import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel

from pypdf import PdfReader

from hr_buddy.app.api.auth import require_admin
from hr_buddy.app.core.config import settings

# Import the shared chat_service so we can trigger re-indexing on upload
from hr_buddy.app.api.routes_chat import chat_service


class DocumentChunk(BaseModel):
    document: str
    content: str


class UpdateChunkRequest(BaseModel):
    chunk_index: int
    new_text: str
    document_name: str


# Managing the knowledge base is for HR admins only
router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"],
    dependencies=[Depends(require_admin)]
)


@router.post("/reload")
def reload_documents():
    """Rebuild the in-memory retrieval index from documents on disk."""
    try:
        chat_service.retrieval.initialize()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload documents: {e}")

    return {"message": "Document index reloaded"}


@router.post("/add-chunks")
def add_document_chunks(chunks: list[DocumentChunk]):
    """Incrementally add pre-chunked documents to the index without rebuilding.

    This endpoint accepts a list of chunks with their metadata (document name, content)
    and adds them to the FAISS index without reprocessing all existing documents.
    """
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks provided")

    try:
        # Convert Pydantic models to dicts
        chunk_dicts = [c.model_dump() for c in chunks]
        chat_service.retrieval.add_documents(chunk_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add chunks: {e}")

    return {"message": f"Added {len(chunks)} chunks to index"}


@router.delete("/by-document")
def delete_document(document_name: str):
    """Delete all chunks belonging to a specific document.

    Query parameter:
    - document_name: name of the document to delete
    """
    if not document_name:
        raise HTTPException(status_code=400, detail="document_name is required")

    try:
        deleted_count = chat_service.retrieval.delete_document(document_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")

    return {"message": f"Deleted {deleted_count} chunks for document '{document_name}'", "deleted_count": deleted_count}


@router.delete("/chunk/{chunk_id}")
def delete_chunk_by_id(chunk_id: int):
    """Delete a specific chunk by its index/ID.

    Path parameter:
    - chunk_id: 0-based index of the chunk to delete
    """
    try:
        success = chat_service.retrieval.delete_chunk(chunk_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Chunk ID {chunk_id} out of range or not found")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting chunk {chunk_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete chunk: {str(e)}")

    if not success:
        raise HTTPException(status_code=404, detail=f"Chunk ID {chunk_id} out of range or not found")

    return {"message": f"Deleted chunk {chunk_id}", "success": success, "chunk_id": chunk_id}


@router.put("/chunk")
def update_chunk(request: UpdateChunkRequest):
    """Update a specific chunk's content and re-embed it.

    Request body:
    - chunk_index: 0-based index of the chunk to update
    - new_text: new content for the chunk
    - document_name: document name for metadata
    """
    try:
        success = chat_service.retrieval.update_chunk(
            request.chunk_index,
            request.new_text,
            request.document_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update chunk: {e}")

    if not success:
        raise HTTPException(status_code=404, detail=f"Chunk index {request.chunk_index} out of range")

    return {"message": f"Updated chunk {request.chunk_index}", "success": success}


@router.get("/chunk/{chunk_id}")
def get_chunk(chunk_id: int):
    """Get a specific chunk by its index/ID.

    Path parameter:
    - chunk_id: 0-based index of the chunk to retrieve
    """
    try:
        chunk = chat_service.retrieval.get_chunk(chunk_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunk: {e}")

    if chunk is None:
        raise HTTPException(status_code=404, detail=f"Chunk ID {chunk_id} out of range or not found")

    return chunk


@router.post("/clear")
def clear_index():
    """Clear all documents and chunks from the index."""
    try:
        chat_service.retrieval.clear_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear index: {e}")

    return {"message": "Index cleared successfully"}


@router.get("/info")
def get_index_info():
    """Get information about the current index state.

    Returns:
    - num_documents: number of unique document chunks in index
    - num_vectors: number of vectors in FAISS index
    - documents_by_name: count of chunks per document
    """
    try:
        info = chat_service.retrieval.get_index_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get index info: {e}")

    return info


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document, save it to the documents folder, and re-index.

    Returns a small preview of the uploaded file and triggers a re-build
    of the in-memory vector index so the new file is immediately searchable.
    """
    documents_dir = Path(settings.DOCUMENTS_PATH)
    documents_dir.mkdir(parents=True, exist_ok=True)

    dest_path = documents_dir / file.filename

    # Allow text and PDF uploads
    allowed_exts = {".txt", ".md", ".pdf"}
    if dest_path.suffix.lower() not in allowed_exts:
        raise HTTPException(status_code=400, detail="Only .txt, .md and .pdf files are supported for upload")

    content = await file.read()

    try:
        dest_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Provide a small preview (first 1000 chars). For PDFs, extract text.
    preview = ""
    try:
        if dest_path.suffix.lower() == ".pdf":
            reader = PdfReader(io.BytesIO(content))
            pages = []
            for p in reader.pages:
                try:
                    pages.append(p.extract_text() or "")
                except Exception:
                    pages.append("")
            preview = "\n\n".join(pages)[:1000]
        else:
            preview = content.decode("utf-8", errors="ignore")[:1000]
    except Exception:
        preview = ""

    # Trigger re-index so uploaded doc becomes searchable immediately
    try:
        chat_service.retrieval.initialize()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Saved file but failed to re-index: {e}")

    return {
        "filename": file.filename,
        "preview": preview,
        "message": "Uploaded and indexed"
    }