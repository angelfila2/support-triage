"""Bearer credentials with separate read and write scopes for this demo API."""

import hmac
import os

from fastapi import HTTPException, Request

# Secure default. AUTH_REQUIRED=false is an explicit local-only demo opt-out.
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"


def authorize(request: Request):
    if not AUTH_REQUIRED:
        return
    writer = os.getenv("API_WRITE_TOKEN", "")
    reader = os.getenv("API_READ_TOKEN", "")
    if len(writer) < 32 or (reader and len(reader) < 32) or (reader and reader == writer):
        raise HTTPException(503, "API credentials are not configured correctly.")
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    if hmac.compare_digest(token.encode(), writer.encode()):
        return
    if reader and hmac.compare_digest(token.encode(), reader.encode()):
        if request.method in {"GET", "HEAD"}:
            return
        raise HTTPException(403, "A write credential is required.")
    raise HTTPException(401, "Invalid credential.", headers={"WWW-Authenticate": "Bearer"})
