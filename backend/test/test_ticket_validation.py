"""Ticket input validation without model calls or ticket database writes."""

import pytest
from pydantic import ValidationError

from backend.api import TicketRequest


def valid_payload():
    return {
        "subject": "Password reset",
        "body": "My password reset link has expired.",
    }


@pytest.mark.parametrize("field", ["subject", "body"])
@pytest.mark.parametrize("invalid_value", ["", "   ", "\t\n", None, 123, True, [], {}])
def test_rejects_blank_or_wrong_type(field, invalid_value):
    payload = valid_payload()
    payload[field] = invalid_value

    with pytest.raises(ValidationError) as error:
        TicketRequest.model_validate(payload)

    assert any(item["loc"] == (field,) for item in error.value.errors())


@pytest.mark.parametrize(("field", "length"), [("subject", 501), ("body", 20001)])
def test_rejects_oversized_text(field, length):
    payload = valid_payload()
    payload[field] = "x" * length

    with pytest.raises(ValidationError) as error:
        TicketRequest.model_validate(payload)

    assert any(item["loc"] == (field,) for item in error.value.errors())


@pytest.mark.parametrize("field", ["subject", "body"])
def test_rejects_missing_required_fields(field):
    payload = valid_payload()
    del payload[field]

    with pytest.raises(ValidationError) as error:
        TicketRequest.model_validate(payload)

    assert any(item["loc"] == (field,) for item in error.value.errors())


def test_trims_surrounding_whitespace():
    request = TicketRequest(
        subject="  Password reset  ",
        body="\n  Please help me reset my password. \t",
    )

    assert request.subject == "Password reset"
    assert request.body == "Please help me reset my password."


def test_accepts_exact_length_limits():
    request = TicketRequest(subject="x" * 500, body="x" * 20000)

    assert len(request.subject) == 500
    assert len(request.body) == 20000


def test_preserves_unicode_and_internal_line_breaks():
    request = TicketRequest(
        subject="  登录问题 🔐  ",
        body="  First line.\n\n第二行。  ",
    )

    assert request.subject == "登录问题 🔐"
    assert request.body == "First line.\n\n第二行。"
