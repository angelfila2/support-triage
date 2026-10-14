from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pathlib import Path
from datetime import datetime

import csv
import uuid
import pandas as pd

from triage import triage_ticket


from config import BASE_DIR, OUTPUT_DIR, TICKETS_FILE, CORS_ORIGINS


# =========================================================
# CSV SCHEMA
# =========================================================

TICKET_COLUMNS = [
    "id",
    "created_at",
    "subject",
    "body",
    "category",
    "urgency",
    "confidence",
    "decision",
    "is_suspicious",
    "reason",
    "response",
    "sla",
    "analysis_correct",
    "corrected_category",
    "review_notes",
    "responded",
    "response_datetime",
    "response_notes",
]


# =========================================================
# CREATE FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Support Ticket Triage API",
    description=(
        "API for classifying, routing, "
        "storing and reviewing support tickets."
    ),
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
SLA_MAP = {
    "SEV1": "4 hours",
    "SEV2": "1 day",
    "SEV3": "3 days",
    "SEV4": "4 days",
    "SEV5": "5 days",
}

# =========================================================
# REQUEST MODELS
# =========================================================

class TicketRequest(BaseModel):
    subject: str
    body: str


class TicketReviewRequest(BaseModel):
    analysis_correct: bool
    corrected_category: str | None = None
    review_notes: str | None = None
class TicketResponseRequest(BaseModel):
    responded: bool
    urgency: str
    response_notes: str | None = None

# =========================================================
# CSV INITIALISATION
# =========================================================
def normalize_ticket(record):
    result = {
        key: None if value == "" else clean_value(value)
        for key, value in record.items()
    }

    result["analysis_correct"] = parse_optional_boolean(
        result.get("analysis_correct")
    )

    result["is_suspicious"] = parse_boolean(
        result.get("is_suspicious")
    )

    result["responded"] = parse_boolean(
        result.get("responded")
    )

    return result
def ensure_ticket_file():
    """
    Creates the output directory and CSV file
    if they do not already exist.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not TICKETS_FILE.exists():
        with open(
            TICKETS_FILE,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=TICKET_COLUMNS,
                quoting=csv.QUOTE_ALL,
            )

            writer.writeheader()


# =========================================================
# VALIDATE CSV SCHEMA
# =========================================================

def validate_ticket_file():
    """
    Ensures that the CSV header matches the
    schema expected by this API.
    """

    ensure_ticket_file()

    try:
        with open(
            TICKETS_FILE,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:

            reader = csv.reader(file)

            header = next(
                reader,
                None,
            )

    except Exception as error:
        raise RuntimeError(
            f"Unable to read ticket CSV: {error}"
        )

    if header != TICKET_COLUMNS:
        raise RuntimeError(
            "\nTicket CSV schema does not match "
            "the current API.\n\n"
            f"Expected:\n{TICKET_COLUMNS}\n\n"
            f"Found:\n{header}\n\n"
            "Delete backend/output/tickets_processed.csv "
            "and restart the API to create a clean file."
        )


# =========================================================
# NORMALISE VALUES
# =========================================================

def clean_value(value):
    """
    Converts values into JSON-safe Python values.
    """

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


# =========================================================
# BOOLEAN HELPERS
# =========================================================

def parse_boolean(value):
    """
    Converts CSV boolean-like values into bool.
    """

    if value is True:
        return True

    if value is False:
        return False

    if value is None:
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
    }


def parse_optional_boolean(value):
    """
    Converts review values into:
    True / False / None.
    """

    if value is None:
        return None

    text = str(value).strip().lower()

    if text in {
        "",
        "nan",
        "none",
    }:
        return None

    if text in {
        "true",
        "1",
        "yes",
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
    }:
        return False

    return None


def generateNextID():
    ids = []

    df = pd.read_csv(TICKETS_FILE)

    for value in df["id"]:
        ids.append(int(value))

    if len(ids) == 0:
        return 1

    return max(ids) + 1
# =========================================================
# SAVE TICKET
# =========================================================

def save_ticket(
    subject: str,
    body: str,
    result: dict,
):
    """
    Saves a completed AI triage result
    as one properly quoted CSV row.
    """

    validate_ticket_file()

    ticket = {
        "id": (
            f"{generateNextID()}"
        ),

        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),

        "subject": subject,
        "body": body,

        "category": result.get(
            "category"
        ),

        "urgency": result.get(
            "urgency"
        ),

        "confidence": result.get(
            "confidence"
        ),

        "decision": result.get(
            "decision"
        ),

        "is_suspicious": result.get(
            "is_suspicious",
            False,
        ),

        "reason": result.get(
            "reason"
        ),

        "response": result.get(
            "response"
        ),

        "sla": result.get(
            "sla"
        ),

        "analysis_correct": None,

        "corrected_category": None,

        "review_notes": None,
        
        "responded": False,
        "response_datetime": None,
        "response_notes": None,
    }

    with open(
        TICKETS_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=TICKET_COLUMNS,
            quoting=csv.QUOTE_ALL,
        )

        writer.writerow(ticket)

    return ticket


# =========================================================
# READ TICKETS
# =========================================================

def read_tickets():
    """
    Reads all stored tickets and converts
    Pandas NaN values to JSON-safe None.
    """

    validate_ticket_file()

    try:
        df = pd.read_csv(
            TICKETS_FILE,
            dtype={
                "id": str,
                "subject": str,
                "body": str,
                "category": str,
                "urgency": str,
                "decision": str,
                "reason": str,
                "response": str,
                "sla": str,
                "corrected_category": str,
                "review_notes": str,
            },
        )

    except pd.errors.EmptyDataError:
        return []

    records = []

    for record in df.to_dict(
        orient="records"
    ):

        cleaned_record = {
            key: clean_value(value)
            for key, value in record.items()
        }

        cleaned_record[
            "analysis_correct"
        ] = parse_optional_boolean(
            cleaned_record.get(
                "analysis_correct"
            )
        )

        cleaned_record[
            "is_suspicious"
        ] = parse_boolean(
            cleaned_record.get(
                "is_suspicious"
            )
        )

        records.append(
            cleaned_record
        )

    return records


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def root():
    return {
        "message": (
            "Support Ticket Triage API is running"
        )
    }


# =========================================================
# TRIAGE TICKET
# =========================================================

@app.post("/api/triage")
def triage(
    request: TicketRequest,
):

    result = triage_ticket(
        request.subject,
        request.body,
    )

    ticket = save_ticket(
        request.subject,
        request.body,
        result,
    )

    return {
        **result,
        "id": ticket["id"],
        "created_at": ticket["created_at"],
    }


# =========================================================
# GET ALL TICKETS
# =========================================================

@app.get("/api/tickets")
def tickets():

    try:
        return read_tickets()

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# =========================================================
# REVIEW TICKET
# =========================================================

@app.patch(
    "/api/tickets/{ticket_id}/review"
)
def review_ticket(
    ticket_id: str,
    review: TicketReviewRequest,
):
    """
    Saves human feedback for a ticket.
    """

    validate_ticket_file()

    try:
        df = pd.read_csv(
            TICKETS_FILE,
            dtype=str,
            keep_default_na=False,
        )

    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=404,
            detail="No tickets exist.",
        )


    # -----------------------------------------------------
    # FIND TICKET
    # -----------------------------------------------------

    matches = (
        df["id"] == ticket_id
    )

    if not matches.any():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Ticket {ticket_id} "
                "was not found."
            ),
        )


    # -----------------------------------------------------
    # VALIDATE REVIEW
    # -----------------------------------------------------

    if (
        review.analysis_correct is False
        and not review.corrected_category
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "corrected_category is required "
                "when the AI classification "
                "is marked incorrect."
            ),
        )


    # -----------------------------------------------------
    # UPDATE REVIEW
    # -----------------------------------------------------

    df.loc[
        matches,
        "analysis_correct",
    ] = str(
        review.analysis_correct
    )

    if review.analysis_correct:
        df.loc[
            matches,
            "corrected_category",
        ] = ""

    else:
        df.loc[
            matches,
            "corrected_category",
        ] = (
            review.corrected_category
            or ""
        )

    df.loc[
        matches,
        "review_notes",
    ] = (
        review.review_notes
        or ""
    )


    # -----------------------------------------------------
    # WRITE CSV
    # -----------------------------------------------------

    df.to_csv(
        TICKETS_FILE,
        index=False,
        columns=TICKET_COLUMNS,
        quoting=csv.QUOTE_ALL,
    )


    # -----------------------------------------------------
    # RETURN UPDATED TICKET
    # -----------------------------------------------------

    updated_row = (
        df.loc[matches]
        .iloc[0]
        .to_dict()
    )

    result = {
        key: (
            None
            if value == ""
            else value
        )
        for key, value
        in updated_row.items()
    }

    result["analysis_correct"] = (
        parse_optional_boolean(
            result.get(
                "analysis_correct"
            )
        )
    )

    result["is_suspicious"] = (
        parse_boolean(
            result.get(
                "is_suspicious"
            )
        )
    )

    return result

@app.patch("/api/tickets/{ticket_id}/respond")
def respond_ticket(ticket_id: str, response: TicketResponseRequest):
    validate_ticket_file()

    try:
        df = pd.read_csv(
            TICKETS_FILE,
            dtype=str,
            keep_default_na=False,
        )
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=404,
            detail="No tickets exist.",
        )

    matches = df["id"] == ticket_id

    if not matches.any():
        raise HTTPException(
            status_code=404,
            detail=f"Ticket {ticket_id} was not found.",
        )

    if response.urgency not in SLA_MAP:
        raise HTTPException(
            status_code=400,
            detail="Invalid severity.",
        )

    df.loc[matches, "urgency"] = response.urgency

    df.loc[matches, "sla"] = SLA_MAP[
        response.urgency
    ]

    df.loc[matches, "responded"] = str(
        response.responded
    )

    df.loc[matches, "response_datetime"] = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    df.loc[matches, "response_notes"] = (
        response.response_notes or ""
    )

    df.to_csv(
        TICKETS_FILE,
        index=False,
        columns=TICKET_COLUMNS,
        quoting=csv.QUOTE_ALL,
    )

    updated_row = (
        df.loc[matches]
        .iloc[0]
        .to_dict()
    )

    return normalize_ticket(updated_row)
# =========================================================
# INITIALISE STORAGE
# =========================================================

ensure_ticket_file()

