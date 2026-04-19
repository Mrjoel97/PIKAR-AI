from unittest.mock import MagicMock, patch


def _reset_embedding_state(embedding_service):
    embedding_service._client = None
    embedding_service._client_disabled_reason = None
    embedding_service._quota_exhausted_until = 0.0


def _clear_vertex_env(monkeypatch):
    """Ensure Vertex AI path is not triggered by stale env vars."""
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)


def test_get_client_uses_api_key(monkeypatch, caplog):
    from app.rag import embedding_service

    _clear_vertex_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    _reset_embedding_state(embedding_service)

    mock_client = MagicMock()
    with patch.object(embedding_service.genai, "Client", return_value=mock_client, create=True) as client_ctor:
        with caplog.at_level("WARNING"):
            client = embedding_service._get_client()

    assert client is mock_client
    client_ctor.assert_called_once_with(api_key="test-api-key")
    assert "GOOGLE_API_KEY not set" not in caplog.text


def test_get_client_falls_back_to_api_key_mode(monkeypatch):
    from app.rag import embedding_service

    _clear_vertex_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    _reset_embedding_state(embedding_service)

    mock_client = MagicMock()
    with patch.object(embedding_service.genai, "Client", return_value=mock_client, create=True) as client_ctor:
        client = embedding_service._get_client()

    assert client is mock_client
    client_ctor.assert_called_once_with(api_key="test-api-key")


def test_get_embedding_health_reports_missing_embedding_credentials(monkeypatch):
    from app.rag import embedding_service

    _clear_vertex_env(monkeypatch)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    _reset_embedding_state(embedding_service)

    health = embedding_service.get_embedding_health()

    assert health["status"] == "unhealthy"
    assert health["reason"] == "missing_google_genai_or_embedding_credentials"


def test_get_embedding_health_accepts_embeddings_list_response(monkeypatch):
    from app.rag import embedding_service

    _clear_vertex_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    _reset_embedding_state(embedding_service)

    mock_client = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1] * embedding_service.EMBEDDING_DIMENSION
    mock_response = MagicMock()
    mock_response.embedding = None
    mock_response.embeddings = [mock_embedding]
    mock_client.models.embed_content.return_value = mock_response

    with patch.object(
        embedding_service.genai, "Client", return_value=mock_client, create=True
    ):
        health = embedding_service.get_embedding_health()

    assert health["status"] == "healthy"
    assert health["dimension"] == embedding_service.EMBEDDING_DIMENSION


def test_build_embed_params_uses_config_task_type():
    from app.rag import embedding_service

    params = embedding_service._build_embed_params("hello")

    assert params["model"] == embedding_service.EMBEDDING_MODEL
    assert params["contents"] == "hello"
    assert params["config"]["taskType"] == embedding_service.EMBEDDING_TASK_TYPE
    assert "task_type" not in params


def test_generate_embeddings_batch_disables_retries_on_api_key_error(monkeypatch, caplog):
    from app.rag import embedding_service

    _clear_vertex_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    _reset_embedding_state(embedding_service)

    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = RuntimeError(
        "400 INVALID_ARGUMENT: API KEY NOT VALID"
    )

    with patch.object(embedding_service.genai, "Client", return_value=mock_client, create=True):
        with caplog.at_level("WARNING"):
            first = embedding_service.generate_embeddings_batch(["a", "b", "c"], batch_size=1)
            second = embedding_service.generate_embeddings_batch(["d"], batch_size=1)

    assert len(first) == 3
    assert len(second) == 1
    assert all(vector == [0.0] * embedding_service.EMBEDDING_DIMENSION for vector in first + second)
    assert mock_client.models.embed_content.call_count == 1
    assert embedding_service._client_disabled_reason == "invalid_api_key"
    assert "invalid" in caplog.text.lower()


def test_generate_embeddings_batch_enters_quota_cooldown(monkeypatch, caplog):
    from app.rag import embedding_service

    _clear_vertex_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    _reset_embedding_state(embedding_service)
    monkeypatch.setattr(embedding_service, "EMBEDDING_QUOTA_COOLDOWN_SECONDS", 60)

    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = RuntimeError(
        "429 RESOURCE_EXHAUSTED: quota exceeded"
    )

    with patch.object(
        embedding_service.genai, "Client", return_value=mock_client, create=True
    ):
        with caplog.at_level("WARNING"):
            first = embedding_service.generate_embeddings_batch(["a", "b"], batch_size=1)
            second = embedding_service.generate_embeddings_batch(["c"], batch_size=1)
            health = embedding_service.get_embedding_health()

    assert len(first) == 2
    assert len(second) == 1
    assert all(
        vector == [0.0] * embedding_service.EMBEDDING_DIMENSION
        for vector in first + second
    )
    assert mock_client.models.embed_content.call_count == 1
    assert embedding_service._client_disabled_reason is None
    assert health["status"] == "unhealthy"
    assert "quota_exhausted_cooldown_active_" in health["reason"]
    assert "quota" in caplog.text.lower()
