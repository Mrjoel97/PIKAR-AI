# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Google Forms service for survey and feedback collection.

Enables agents to:
- Create customer surveys
- Build feedback forms
- Retrieve form responses for analysis
"""

from dataclasses import dataclass
from typing import Any, Literal

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build


@dataclass
class FormInfo:
    """Information about a Google Form."""

    id: str
    title: str
    url: str
    edit_url: str
    response_count: int = 0


@dataclass
class FormQuestion:
    """Represents a form question."""

    question_id: str
    title: str
    question_type: str
    required: bool = False


class GoogleFormsService:
    """Service for Google Forms operations.

    Provides methods for:
    - Creating forms with various question types
    - Retrieving responses
    - Managing form settings
    """

    def __init__(self, credentials: Credentials):
        """Initialize with Google OAuth credentials."""
        self.credentials = credentials
        self._forms_service: Resource | None = None
        self._drive_service: Resource | None = None

    @property
    def forms(self) -> Resource:
        """Lazy-load Forms API service."""
        if self._forms_service is None:
            self._forms_service = build("forms", "v1", credentials=self.credentials)
        return self._forms_service

    @property
    def drive(self) -> Resource:
        """Lazy-load Drive API."""
        if self._drive_service is None:
            self._drive_service = build("drive", "v3", credentials=self.credentials)
        return self._drive_service

    def create_form(
        self,
        title: str,
        description: str | None = None,
    ) -> FormInfo:
        """Create a new Google Form.

        Args:
            title: Form title.
            description: Optional description.

        Returns:
            FormInfo with ID and URLs.
        """
        form_body = {"info": {"title": title}}

        if description:
            form_body["info"]["documentTitle"] = title

        result = self.forms.forms().create(body=form_body).execute()
        form_id = result.get("formId")

        # Add description if provided
        if description:
            self.forms.forms().batchUpdate(
                formId=form_id,
                body={
                    "requests": [
                        {
                            "updateFormInfo": {
                                "info": {"description": description},
                                "updateMask": "description",
                            }
                        }
                    ]
                },
            ).execute()

        return FormInfo(
            id=form_id,
            title=title,
            url=f"https://docs.google.com/forms/d/{form_id}/viewform",
            edit_url=f"https://docs.google.com/forms/d/{form_id}/edit",
        )

    def add_question(
        self,
        form_id: str,
        title: str,
        question_type: Literal[
            "text", "paragraph", "multiple_choice", "checkbox", "scale", "date"
        ],
        options: list[str] | None = None,
        required: bool = False,
        index: int | None = None,
    ) -> dict[str, Any]:
        """Add a question to a form.

        Args:
            form_id: The form ID.
            title: Question text.
            question_type: Type of question.
            options: Options for multiple choice/checkbox.
            required: Whether the question is required.
            index: Position in form (appends if None).

        Returns:
            Created question details.
        """
        # Build question based on type
        question_item: dict[str, Any] = {
            "title": title,
            "questionItem": {
                "question": {
                    "required": required,
                }
            },
        }

        question = question_item["questionItem"]["question"]

        if question_type == "text":
            question["textQuestion"] = {"paragraph": False}
        elif question_type == "paragraph":
            question["textQuestion"] = {"paragraph": True}
        elif question_type == "multiple_choice":
            question["choiceQuestion"] = {
                "type": "RADIO",
                "options": [{"value": opt} for opt in (options or ["Option 1"])],
            }
        elif question_type == "checkbox":
            question["choiceQuestion"] = {
                "type": "CHECKBOX",
                "options": [{"value": opt} for opt in (options or ["Option 1"])],
            }
        elif question_type == "scale":
            question["scaleQuestion"] = {
                "low": 1,
                "high": 5,
                "lowLabel": "Poor",
                "highLabel": "Excellent",
            }
        elif question_type == "date":
            question["dateQuestion"] = {}

        request = {
            "createItem": {
                "item": question_item,
                "location": {"index": index if index is not None else 0},
            }
        }

        self.forms.forms().batchUpdate(
            formId=form_id,
            body={"requests": [request]},
        ).execute()

        return {"status": "success", "question_added": title}

    def get_responses(
        self,
        form_id: str,
    ) -> list[dict[str, Any]]:
        """Get all responses for a form.

        Args:
            form_id: The form ID.

        Returns:
            List of responses with answers.
        """
        result = self.forms.forms().responses().list(formId=form_id).execute()
        responses = result.get("responses", [])

        parsed_responses = []
        for response in responses:
            answers = response.get("answers", {})
            parsed = {
                "response_id": response.get("responseId"),
                "submitted_at": response.get("createTime"),
                "answers": {},
            }

            for question_id, answer_data in answers.items():
                text_answers = answer_data.get("textAnswers", {}).get("answers", [])
                if text_answers:
                    parsed["answers"][question_id] = [
                        a.get("value") for a in text_answers
                    ]

            parsed_responses.append(parsed)

        return parsed_responses

    def get_form(self, form_id: str) -> dict[str, Any]:
        """Get form details including questions.

        Args:
            form_id: The form ID.

        Returns:
            Form metadata and questions.
        """
        result = self.forms.forms().get(formId=form_id).execute()

        questions = []
        for item in result.get("items", []):
            if "questionItem" in item:
                q = item["questionItem"]["question"]
                questions.append(
                    {
                        "id": q.get("questionId"),
                        "title": item.get("title"),
                        "required": q.get("required", False),
                    }
                )

        return {
            "id": result.get("formId"),
            "title": result.get("info", {}).get("title"),
            "description": result.get("info", {}).get("description"),
            "url": f"https://docs.google.com/forms/d/{form_id}/viewform",
            "questions": questions,
        }

    def create_feedback_form(
        self,
        title: str,
        business_name: str,
        questions: list[dict[str, Any]] | None = None,
    ) -> FormInfo:
        """Create a customer feedback form with standard questions.

        Args:
            title: Form title (e.g., "Customer Satisfaction Survey").
            business_name: Name of the business.
            questions: Optional custom questions.

        Returns:
            Created form info.
        """
        # Create the form
        form = self.create_form(
            title=title,
            description=f"Help {business_name} improve by sharing your feedback.",
        )

        # Add standard feedback questions
        standard_questions = questions or [
            {
                "title": "How satisfied are you with our service?",
                "type": "scale",
                "required": True,
            },
            {
                "title": "What did you like most?",
                "type": "paragraph",
                "required": False,
            },
            {"title": "What could we improve?", "type": "paragraph", "required": False},
            {
                "title": "Would you recommend us to others?",
                "type": "multiple_choice",
                "options": [
                    "Definitely yes",
                    "Probably yes",
                    "Not sure",
                    "Probably no",
                    "Definitely no",
                ],
                "required": True,
            },
            {
                "title": "Any additional comments?",
                "type": "paragraph",
                "required": False,
            },
        ]

        for i, q in enumerate(standard_questions):
            self.add_question(
                form_id=form.id,
                title=q["title"],
                question_type=q["type"],
                options=q.get("options"),
                required=q.get("required", False),
                index=i,
            )

        return form


def get_forms_service(credentials: Credentials) -> GoogleFormsService:
    """Get Forms service instance."""
    return GoogleFormsService(credentials)
