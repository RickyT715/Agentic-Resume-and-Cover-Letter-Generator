"""Tests for the RAG pipeline components."""


class TestChunker:
    """Tests for text chunking."""

    def test_empty_text(self):
        from rag.chunker import chunk_text

        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        from rag.chunker import chunk_text

        text = "This is a short sentence."
        chunks = chunk_text(text, chunk_size=1000)
        assert len(chunks) == 1
        assert text in chunks[0]

    def test_long_text_multiple_chunks(self):
        from rag.chunker import chunk_text

        text = (
            "First paragraph about the company.\n\nSecond paragraph about culture.\n\nThird paragraph about tech stack."
        )
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=0)
        assert len(chunks) > 1

    def test_chunk_overlap(self):
        from rag.chunker import chunk_text

        text = "A" * 200 + "\n\n" + "B" * 200 + "\n\n" + "C" * 200
        chunks = chunk_text(text, chunk_size=250, chunk_overlap=50)
        if len(chunks) > 1:
            # Second chunk should contain some content from first chunk's end
            assert len(chunks[1]) > 200

    def test_prepare_chunks_with_metadata(self):
        from rag.chunker import prepare_chunks_with_metadata

        chunks = ["chunk1", "chunk2"]
        result = prepare_chunks_with_metadata(
            chunks=chunks,
            source_url="https://example.com",
            company_name="TestCo",
            content_type="about",
        )
        assert len(result) == 2
        assert result[0]["text"] == "chunk1"
        assert result[0]["metadata"]["company_name"] == "testco"
        assert result[0]["metadata"]["content_type"] == "about"
        assert result[0]["metadata"]["chunk_index"] == 0

    def test_filters_short_chunks(self):
        from rag.chunker import chunk_text

        text = "A\n\nB\n\nThis is a sufficiently long chunk of text."
        chunks = chunk_text(text, chunk_size=30, chunk_overlap=0)
        # Very short chunks like "A" and "B" should be filtered
        for chunk in chunks:
            assert len(chunk) > 20


class TestEmbeddings:
    """Tests for embedding functions."""

    def test_fallback_embeddings(self):
        from rag.embeddings import _simple_embedding_fn

        texts = ["hello world", "test text"]
        embeddings = _simple_embedding_fn(texts)
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384
        # Different texts should produce different embeddings
        assert embeddings[0] != embeddings[1]

    def test_embed_texts_returns_correct_shape(self):
        from rag.embeddings import embed_texts

        texts = ["hello", "world"]
        embeddings = embed_texts(texts)
        assert len(embeddings) == 2
        assert isinstance(embeddings[0], list)
        assert len(embeddings[0]) > 0


class TestRetriever:
    """Tests for retrieval utilities."""

    def test_grade_relevance(self):
        from rag.retriever import _grade_relevance

        results = [
            {"text": "relevant", "distance": 0.3},
            {"text": "irrelevant", "distance": 0.9},
            {"text": "borderline", "distance": 0.6},
        ]
        relevant, irrelevant = _grade_relevance(results, threshold=0.6)
        assert len(relevant) == 2  # 0.3 and 0.6
        assert len(irrelevant) == 1  # 0.9

    def test_rewrite_query(self):
        from rag.retriever import _rewrite_query

        query = "What is the company culture at Google?"
        rewritten = _rewrite_query(query)
        assert "company" in rewritten
        assert "culture" in rewritten
        assert "google" in rewritten
        # Stop words should be removed
        assert "what" not in rewritten
        assert "the" not in rewritten

    def test_rewrite_query_with_context(self):
        from rag.retriever import _rewrite_query

        query = "tech stack and engineering"
        rewritten = _rewrite_query(query, context="Google")
        assert "Google" in rewritten


class TestScraper:
    """Tests for scraping utilities."""

    def test_extract_text_from_html(self):
        from rag.scraper import _extract_text_from_html

        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <script>var x = 1;</script>
            <style>.foo { color: red; }</style>
            <nav>Navigation</nav>
            <main>
                <h1>Hello World</h1>
                <p>This is the main content.</p>
            </main>
            <footer>Footer</footer>
        </body>
        </html>
        """
        text = _extract_text_from_html(html)
        assert "Hello World" in text
        assert "main content" in text
        # Script/style/nav/footer should be removed (with BeautifulSoup)
        assert "var x" not in text

    def test_extract_text_plain_html(self):
        from rag.scraper import _extract_text_from_html

        html = "<p>Simple paragraph</p>"
        text = _extract_text_from_html(html)
        assert "Simple paragraph" in text
