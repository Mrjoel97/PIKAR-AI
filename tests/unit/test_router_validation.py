# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for community router Pydantic validation constraints."""

import pytest
from pydantic import ValidationError

from app.routers.community import CreateCommentRequest, CreatePostRequest


class TestCreatePostRequestTitle:
    """Tests for title field constraints."""

    def test_title_rejects_above_200_chars(self):
        """Title longer than 200 characters must be rejected."""
        with pytest.raises(ValidationError):
            CreatePostRequest(title="x" * 201, body="valid body")

    def test_title_accepts_exactly_200_chars(self):
        """Title of exactly 200 characters must be accepted."""
        post = CreatePostRequest(title="x" * 200, body="valid body")
        assert len(post.title) == 200

    def test_title_rejects_empty_string(self):
        """Empty title must be rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            CreatePostRequest(title="", body="valid body")

    def test_title_accepts_normal_length(self):
        """Normal title is accepted."""
        post = CreatePostRequest(title="My Great Post", body="Some body content")
        assert post.title == "My Great Post"


class TestCreatePostRequestBody:
    """Tests for body field constraints."""

    def test_body_rejects_above_10000_chars(self):
        """Body longer than 10000 characters must be rejected."""
        with pytest.raises(ValidationError):
            CreatePostRequest(title="valid title", body="x" * 10_001)

    def test_body_accepts_exactly_10000_chars(self):
        """Body of exactly 10000 characters must be accepted."""
        post = CreatePostRequest(title="valid title", body="x" * 10_000)
        assert len(post.body) == 10_000

    def test_body_rejects_empty_string(self):
        """Empty body must be rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            CreatePostRequest(title="valid title", body="")


class TestCreatePostRequestTags:
    """Tests for tags field constraints."""

    def test_tags_rejects_list_with_11_items(self):
        """Tags list with 11+ items must be rejected."""
        tags = [f"tag{i}" for i in range(11)]
        with pytest.raises(ValidationError):
            CreatePostRequest(title="valid title", body="valid body", tags=tags)

    def test_tags_accepts_exactly_10_items(self):
        """Tags list with exactly 10 items must be accepted."""
        tags = [f"tag{i}" for i in range(10)]
        post = CreatePostRequest(title="valid title", body="valid body", tags=tags)
        assert len(post.tags) == 10

    def test_tags_rejects_individual_tag_above_50_chars(self):
        """Individual tag longer than 50 characters must be rejected."""
        with pytest.raises(ValidationError):
            CreatePostRequest(
                title="valid title",
                body="valid body",
                tags=["x" * 51],
            )

    def test_tags_accepts_individual_tag_of_exactly_50_chars(self):
        """Individual tag of exactly 50 characters must be accepted."""
        post = CreatePostRequest(
            title="valid title",
            body="valid body",
            tags=["x" * 50],
        )
        assert post.tags[0] == "x" * 50

    def test_tags_can_be_none(self):
        """Tags field can be None (optional)."""
        post = CreatePostRequest(title="valid title", body="valid body", tags=None)
        assert post.tags is None

    def test_tags_strips_whitespace(self):
        """Tags with surrounding whitespace should be stripped."""
        post = CreatePostRequest(
            title="valid title",
            body="valid body",
            tags=["  python  ", " ai "],
        )
        assert post.tags == ["python", "ai"]

    def test_tags_rejects_blank_tag(self):
        """Tags that are blank after stripping should be rejected."""
        with pytest.raises(ValidationError):
            CreatePostRequest(
                title="valid title",
                body="valid body",
                tags=["   "],
            )


class TestCreatePostRequestCategory:
    """Tests for category field constraints."""

    def test_category_rejects_above_50_chars(self):
        """Category longer than 50 characters must be rejected."""
        with pytest.raises(ValidationError):
            CreatePostRequest(
                title="valid title",
                body="valid body",
                category="x" * 51,
            )

    def test_category_accepts_exactly_50_chars(self):
        """Category of exactly 50 characters must be accepted."""
        post = CreatePostRequest(
            title="valid title",
            body="valid body",
            category="x" * 50,
        )
        assert len(post.category) == 50

    def test_category_defaults_to_general(self):
        """Category defaults to 'general' when not provided."""
        post = CreatePostRequest(title="valid title", body="valid body")
        assert post.category == "general"

    def test_category_can_be_none(self):
        """Category can be set to None."""
        post = CreatePostRequest(title="valid title", body="valid body", category=None)
        assert post.category is None


class TestCreateCommentRequest:
    """Tests for CreateCommentRequest validation."""

    def test_body_rejects_above_5000_chars(self):
        """Comment body longer than 5000 characters must be rejected."""
        with pytest.raises(ValidationError):
            CreateCommentRequest(body="x" * 5_001)

    def test_body_accepts_exactly_5000_chars(self):
        """Comment body of exactly 5000 characters must be accepted."""
        comment = CreateCommentRequest(body="x" * 5_000)
        assert len(comment.body) == 5_000

    def test_body_rejects_empty_string(self):
        """Empty comment body must be rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            CreateCommentRequest(body="")

    def test_body_accepts_normal_content(self):
        """Normal comment body is accepted."""
        comment = CreateCommentRequest(body="Great post, thanks!")
        assert comment.body == "Great post, thanks!"
