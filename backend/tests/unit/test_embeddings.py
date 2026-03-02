"""
Unit tests for the embeddings service.

Tests vector store operations with mocked OpenAI and Firestore.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestEmbeddingsService:
    """Tests for EmbeddingsService"""

    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client"""
        with patch('services.embeddings.OpenAI') as mock:
            client = MagicMock()
            mock.return_value = client

            # Mock embedding response
            embedding_response = MagicMock()
            embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
            client.embeddings.create.return_value = embedding_response

            yield client

    @pytest.fixture
    def mock_firestore(self):
        """Mock Firestore client and collection"""
        with patch('services.embeddings.get_firestore_client') as mock_get_client:
            db = MagicMock()
            mock_get_client.return_value = db

            collection = MagicMock()
            db.collection.return_value = collection

            # Mock batch for add operations
            batch = MagicMock()
            db.batch.return_value = batch

            yield {
                'db': db,
                'collection': collection,
                'batch': batch
            }

    @pytest.fixture
    def mock_vector(self):
        """Mock Firestore Vector class"""
        with patch('services.embeddings.Vector') as mock:
            mock.side_effect = lambda x: x  # Just return the input
            yield mock

    @pytest.fixture
    def service(self, mock_openai, mock_firestore, mock_vector):
        """Create EmbeddingsService with mocked dependencies"""
        with patch('services.embeddings.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                from services.embeddings import EmbeddingsService
                svc = EmbeddingsService()
                svc._openai_client = mock_openai
                svc._db = mock_firestore['db']
                svc._collection = mock_firestore['collection']
                svc._initialized = True
                return svc

    def test_generate_embedding(self, service, mock_openai):
        """Should generate embedding for text"""
        result = service.generate_embedding("test text")

        assert result == [0.1] * 1536
        mock_openai.embeddings.create.assert_called_once()

    def test_generate_embeddings_batch(self, service, mock_openai):
        """Should generate embeddings for multiple texts"""
        # Setup batch response
        mock_openai.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]

        result = service.generate_embeddings(["text1", "text2"])

        assert len(result) == 2
        mock_openai.embeddings.create.assert_called_once()

    def test_add_document(self, service, mock_firestore, mock_openai):
        """Should add document to vector store"""
        service.add_document(
            content="This is test content for embedding.",
            source="Test Source",
            metadata={"type": "test"}
        )

        # Should have called batch.set for each chunk
        mock_firestore['batch'].set.assert_called()
        mock_firestore['batch'].commit.assert_called_once()

    def test_search(self, service, mock_firestore, mock_openai):
        """Should search for similar documents"""
        # Setup vector query mock
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            'content': 'Document content',
            'source': 'Test Source',
            'metadata': {}
        }
        mock_doc.distance = 0.1

        vector_query = MagicMock()
        vector_query.stream.return_value = [mock_doc]
        mock_firestore['collection'].find_nearest.return_value = vector_query

        results = service.search("test query", n_results=5)

        assert len(results) == 1
        assert results[0].content == 'Document content'
        assert results[0].source == 'Test Source'
        mock_firestore['collection'].find_nearest.assert_called_once()

    def test_search_empty_results(self, service, mock_firestore, mock_openai):
        """Should handle empty search results"""
        vector_query = MagicMock()
        vector_query.stream.return_value = []
        mock_firestore['collection'].find_nearest.return_value = vector_query

        results = service.search("no match query")

        assert len(results) == 0

    def test_get_document_count(self, service, mock_firestore):
        """Should return document count"""
        # Mock limit().stream() to return 42 docs
        mock_docs = [MagicMock() for _ in range(42)]
        mock_firestore['collection'].limit.return_value.stream.return_value = mock_docs

        count = service.get_document_count()

        assert count == 42

    def test_chunk_text(self, service):
        """Should chunk long text into smaller pieces"""
        long_text = "This is a sentence. " * 100  # ~2000 chars

        chunks = service._chunk_text(long_text, "test_source", {})

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.source == "test_source"
            assert len(chunk.content) <= service.CHUNK_SIZE + 50  # Allow some overlap

    def test_chunk_text_short(self, service):
        """Should handle short text as single chunk"""
        short_text = "This is short."

        chunks = service._chunk_text(short_text, "test_source", {})

        assert len(chunks) == 1
        assert chunks[0].content == short_text

    def test_clear(self, service, mock_firestore):
        """Should clear all documents from vector store"""
        # Mock documents to delete
        mock_doc1 = MagicMock()
        mock_doc2 = MagicMock()
        mock_firestore['collection'].limit.return_value.stream.side_effect = [
            [mock_doc1, mock_doc2],  # First batch
            []  # Empty to stop loop
        ]

        deleted = service.clear()

        assert deleted == 2
        mock_firestore['batch'].delete.assert_called()
        mock_firestore['batch'].commit.assert_called()

    def test_document_exists(self, service, mock_firestore):
        """Should check if document exists"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_firestore['collection'].document.return_value.get.return_value = mock_doc

        exists = service.document_exists("test-id")

        assert exists is True
        mock_firestore['collection'].document.assert_called_with("test-id")


class TestEmbeddingsServiceInitialization:
    """Tests for service initialization and error handling"""

    def test_missing_api_key_raises_error(self):
        """Should raise error if OPENAI_API_KEY not set"""
        with patch('services.embeddings.OPENAI_AVAILABLE', True):
            with patch.dict('os.environ', {}, clear=True):
                # Remove OPENAI_API_KEY if it exists
                import os
                if 'OPENAI_API_KEY' in os.environ:
                    del os.environ['OPENAI_API_KEY']

                from services.embeddings import EmbeddingsService
                service = EmbeddingsService()

                with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                    service._ensure_initialized()

    def test_missing_openai_package(self):
        """Should raise error if openai package not available"""
        with patch('services.embeddings.OPENAI_AVAILABLE', False):
            from services.embeddings import EmbeddingsService
            service = EmbeddingsService()

            with pytest.raises(RuntimeError, match="OpenAI package not installed"):
                service._ensure_initialized()


class TestDocumentChunk:
    """Tests for DocumentChunk dataclass"""

    def test_document_chunk_creation(self):
        """Should create DocumentChunk with all fields"""
        from services.embeddings import DocumentChunk

        chunk = DocumentChunk(
            id="test-id",
            content="Test content",
            source="Test Source",
            metadata={"key": "value"}
        )

        assert chunk.id == "test-id"
        assert chunk.content == "Test content"
        assert chunk.source == "Test Source"
        assert chunk.metadata == {"key": "value"}


class TestSearchResult:
    """Tests for SearchResult dataclass"""

    def test_search_result_creation(self):
        """Should create SearchResult with all fields"""
        from services.embeddings import SearchResult

        result = SearchResult(
            content="Found content",
            source="Source",
            score=0.95,
            metadata={"type": "test"}
        )

        assert result.content == "Found content"
        assert result.source == "Source"
        assert result.score == 0.95
        assert result.metadata == {"type": "test"}
