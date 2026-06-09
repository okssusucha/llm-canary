from llm_canary.semantic import HashEmbedder, cosine, similarity


def test_identical_texts_have_similarity_one():
    emb = HashEmbedder()
    assert similarity(emb, "refund within 30 days", "refund within 30 days") == 1.0


def test_disjoint_texts_score_low():
    emb = HashEmbedder()
    score = similarity(emb, "quarterly sales report", "banana smoothie recipe")
    assert score < 0.5


def test_paraphrase_scores_higher_than_unrelated():
    emb = HashEmbedder()
    base = "you can get a refund within 30 days of purchase"
    close = "a refund is available within 30 days after purchase"
    far = "the weather in busan is sunny today"
    assert similarity(emb, base, close) > similarity(emb, base, far)


def test_embedding_is_deterministic():
    emb = HashEmbedder()
    assert emb.embed("stable output") == emb.embed("stable output")


def test_cosine_zero_vectors():
    assert cosine([0.0, 0.0], [0.0, 0.0]) == 1.0
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0
