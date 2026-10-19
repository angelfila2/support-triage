"""Validate human review data without model calls or ticket database writes."""

import pytest
from pydantic import ValidationError

from backend.api import TicketReviewRequest


@pytest.mark.parametrize("category", [
    "password_reset", "billing_question", "shipping_delay", "login_issues", "other",
])
def test_accepts_supported_correction_categories(category):
    review = TicketReviewRequest(analysis_correct=False, corrected_category=category)
    assert review.corrected_category == category


@pytest.mark.parametrize("category", [
    "unknown", "escalate", "AUTO_REPLY", "billing", "", "   ", None,
])
def test_incorrect_review_requires_a_supported_category(category):
    with pytest.raises(ValidationError):
        TicketReviewRequest(analysis_correct=False, corrected_category=category)


def test_incorrect_review_cannot_omit_category():
    with pytest.raises(ValidationError):
        TicketReviewRequest(analysis_correct=False)


def test_correct_review_needs_no_correction():
    review = TicketReviewRequest(analysis_correct=True)
    assert review.corrected_category is None
    assert review.review_notes is None


def test_correct_review_clears_an_unneeded_valid_correction():
    review = TicketReviewRequest(analysis_correct=True, corrected_category="login_issues")
    assert review.corrected_category is None


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None])
def test_review_decision_requires_a_real_boolean(value):
    with pytest.raises(ValidationError):
        TicketReviewRequest(analysis_correct=value, corrected_category="other")


def test_trims_category_and_notes():
    review = TicketReviewRequest(
        analysis_correct=False,
        corrected_category="  login_issues  ",
        review_notes="  The customer cannot sign in.\n",
    )
    assert review.corrected_category == "login_issues"
    assert review.review_notes == "The customer cannot sign in."


def test_accepts_notes_at_length_limit():
    review = TicketReviewRequest(analysis_correct=True, review_notes="x" * 5000)
    assert len(review.review_notes) == 5000


def test_rejects_oversized_notes():
    with pytest.raises(ValidationError):
        TicketReviewRequest(analysis_correct=True, review_notes="x" * 5001)


@pytest.mark.parametrize("value", [123, True, [], {}])
def test_notes_require_a_string_or_none(value):
    with pytest.raises(ValidationError):
        TicketReviewRequest(analysis_correct=True, review_notes=value)
