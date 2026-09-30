from hr_buddy.app.core.config import settings


class TextChunker:

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP
    ):

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str):

        chunks = []

        start = 0

        while start < len(text):

            end = start + self.chunk_size

            chunk = text[start:end]

            chunks.append(chunk)

            start = end - self.chunk_overlap

        return chunks