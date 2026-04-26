import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch, sentinel

import google

from app.services import vertex_video_service


def _video_operation(*, uri: str | None = None, video_bytes: bytes | None = None):
    return SimpleNamespace(
        done=True,
        result=SimpleNamespace(
            generated_videos=[
                SimpleNamespace(
                    video=SimpleNamespace(uri=uri, video_bytes=video_bytes)
                )
            ]
        ),
    )


def _install_fake_google_genai(*, client: MagicMock, image_factory=None):
    fake_genai = ModuleType("google.genai")
    fake_genai.Client = MagicMock(return_value=client)

    fake_types = ModuleType("google.genai.types")
    fake_types.GenerateVideosConfig = lambda **kwargs: SimpleNamespace(**kwargs)
    fake_types.Image = image_factory or (lambda **kwargs: SimpleNamespace(**kwargs))

    return patch.dict(
        sys.modules,
        {
            "google.genai": fake_genai,
            "google.genai.types": fake_types,
        },
    ), patch.object(google, "genai", fake_genai, create=True), fake_types


def test_generate_video_with_sdk_uses_image_argument_for_image_to_video():
    client = MagicMock()
    client.models.generate_videos.return_value = _video_operation(
        uri="https://example.com/video.mp4"
    )
    png_bytes = b"\x89PNG\r\n\x1a\nmock-image"
    image_mock = MagicMock(return_value=sentinel.image_payload)

    module_patch, attr_patch, _fake_types = _install_fake_google_genai(
        client=client,
        image_factory=image_mock,
    )
    with module_patch, attr_patch:
        result = vertex_video_service._generate_video_with_sdk(
            project="pikar-ai",
            location="us-central1",
            model_id="veo-3.1-fast-generate-001",
            prompt="benchmark prompt",
            duration_seconds=8,
            aspect_ratio="16:9",
            number_of_videos=1,
            image_bytes=png_bytes,
        )

    assert result["success"] is True
    kwargs = client.models.generate_videos.call_args.kwargs
    assert kwargs["prompt"] == "benchmark prompt"
    assert kwargs["image"] is sentinel.image_payload
    image_mock.assert_called_once_with(image_bytes=png_bytes, mime_type="image/png")


def test_generate_video_with_sdk_downloads_gcs_uri_when_bytes_missing():
    client = MagicMock()
    client.models.generate_videos.return_value = _video_operation(
        uri="gs://video-bucket/clip.mp4"
    )

    module_patch, attr_patch, _fake_types = _install_fake_google_genai(client=client)
    with module_patch, attr_patch, patch(
        "app.services.vertex_video_service._download_remote_video_bytes",
        return_value=(b"video-bytes", None),
    ) as download_mock:
        result = vertex_video_service._generate_video_with_sdk(
            project="pikar-ai-project",
            location="us-central1",
            model_id="veo-test",
            prompt="Launch video",
            duration_seconds=4,
            aspect_ratio="16:9",
            number_of_videos=1,
        )

    assert result["success"] is True
    assert result["video_bytes"] == b"video-bytes"
    assert result["video_url"] == "gs://video-bucket/clip.mp4"
    download_mock.assert_called_once_with(
        "gs://video-bucket/clip.mp4",
        project="pikar-ai-project",
    )


def test_generate_video_with_sdk_fails_when_gcs_uri_download_fails():
    client = MagicMock()
    client.models.generate_videos.return_value = _video_operation(
        uri="gs://video-bucket/clip.mp4"
    )

    module_patch, attr_patch, _fake_types = _install_fake_google_genai(client=client)
    with module_patch, attr_patch, patch(
        "app.services.vertex_video_service._download_remote_video_bytes",
        return_value=(None, "permission denied"),
    ):
        result = vertex_video_service._generate_video_with_sdk(
            project="pikar-ai-project",
            location="us-central1",
            model_id="veo-test",
            prompt="Launch video",
            duration_seconds=4,
            aspect_ratio="16:9",
            number_of_videos=1,
        )

    assert result["success"] is False
    assert result["video_bytes"] is None
    assert result["video_url"] is None
    assert result["error"] == "permission denied"
