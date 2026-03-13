from unittest.mock import MagicMock, patch


def _reset_embedding_state(embedding_service):
    embedding_service._client = None
    embedding_service._client_disabled_reason = None


def test_get_client_uses_api_key(monkeypatch, caplog):
    from app.rag import embedding_service

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

    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    _reset_embedding_state(embedding_service)

    mock_client = MagicMock()
    with patch.object(embedding_service.genai, "Client", return_value=mock_client, create=True) as client_ctor:
        client = embedding_service._get_client()

    assert client is mock_client
    client_ctor.assert_called_once_with(api_key="test-api-key")


def test_get_embedding_health_reports_missing_embedding_credentials(monkeypatch):
    from app.rag import embedding_service

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    _reset_embedding_state(embedding_service)

    health = embedding_service.get_embedding_health()

    assert health["status"] == "unhealthy"
    assert health["reason"] == "missing_google_genai_or_embedding_credentials"


def test_build_embed_params_uses_config_task_type():
    from app.rag import embedding_service

    params = embedding_service._build_embed_params("hello")

    assert params["model"] == embedding_service.EMBEDDING_MODEL
    assert params["contents"] == "hello"
    assert params["config"]["taskType"] == embedding_service.EMBEDDING_TASK_TYPE
    assert "task_type" not in params


def test_generate_embeddings_batch_disables_retries_on_api_key_error(monkeypatch, caplog):
    from app.rag import embedding_service

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
