from unittest.mock import patch

from app.commerce.invoice_service import InvoiceService
from app.workflows.generator import WorkflowGenerator


def test_workflow_generator_uses_sdk_compatible_http_retry_fields():
    retry_options = object()

    with (
        patch(
            "app.workflows.generator.types.HttpRetryOptions",
            return_value=retry_options,
        ) as mock_retry,
        patch("app.workflows.generator.Gemini") as mock_gemini,
        patch("app.workflows.generator.get_workflow_engine", return_value="engine"),
    ):
        generator = WorkflowGenerator()

    mock_retry.assert_called_once_with(
        attempts=5,
        initial_delay=2.0,
        exp_base=2.0,
        max_delay=60.0,
    )
    assert mock_gemini.call_args.kwargs["retry_options"] is retry_options
    assert generator.engine == "engine"


def test_invoice_service_uses_sdk_compatible_http_retry_fields():
    retry_options = object()

    with (
        patch(
            "app.commerce.invoice_service.types.HttpRetryOptions",
            return_value=retry_options,
        ) as mock_retry,
        patch("app.commerce.invoice_service.Gemini") as mock_gemini,
    ):
        InvoiceService()

    mock_retry.assert_called_once_with(
        attempts=5,
        initial_delay=2.0,
        exp_base=2.0,
        max_delay=60.0,
    )
    assert mock_gemini.call_args.kwargs["retry_options"] is retry_options
