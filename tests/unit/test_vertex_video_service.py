from types import SimpleNamespace
from unittest.mock import Mock, patch, sentinel

from app.services.vertex_video_service import _generate_video_with_sdk


def test_generate_video_with_sdk_uses_image_argument_for_image_to_video():
    operation = SimpleNamespace(
        done=True,
        result=SimpleNamespace(
            generated_videos=[SimpleNamespace(video=SimpleNamespace(uri="https://example.com/video.mp4", video_bytes=None))]
        ),
    )
    client = Mock()
    client.models.generate_videos.return_value = operation

    png_bytes = b"\x89PNG\r\n\x1a\nmock-image"

    with patch("google.genai.Client", return_value=client, create=True), patch(
        "google.genai.types.Image", return_value=sentinel.image_payload
    ) as image_mock:
        result = _generate_video_with_sdk(
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
