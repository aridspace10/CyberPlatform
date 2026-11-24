"""Public issue reporting endpoint."""

import logging
import re
import smtplib
from enum import Enum

from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from services.auth_rate_limit import enforce_auth_rate_limit
from services.contact_email import EmailNotConfigured, send_contact_report
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contact", tags=["contact"])
EMAIL_PATTERN = re.compile(r"^[^\s@<>,;:]+@[^\s@<>,;:]+\.[^\s@<>,;:]+$")


class Category(str, Enum):
    bug = "bug"
    account = "account"
    gameplay = "gameplay"
    suggestion = "suggestion"
    other = "other"


class ContactReport(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    category: Category
    subject: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    steps: str = Field(default="", max_length=2000)
    expected: str = Field(default="", max_length=1000)
    actual: str = Field(default="", max_length=1000)
    page: str = Field(default="", max_length=300)
    device: str = Field(default="", max_length=300)

    @field_validator(
        "name",
        "email",
        "subject",
        "description",
        "steps",
        "expected",
        "actual",
        "page",
        "device",
        mode="before",
    )
    @classmethod
    def trim_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("name", "subject", "description")
    @classmethod
    def require_content(cls, value: str) -> str:
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("subject")
    @classmethod
    def single_line_subject(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("Subject must be one line")
        return value


@router.post("", status_code=201)
def submit_contact(
    report: ContactReport, request: Request, db: Session = Depends(get_db)
):
    enforce_auth_rate_limit(db, request, "contact")
    try:
        reference = send_contact_report(report)
    except (EmailNotConfigured, ValueError) as exc:
        logger.error("Contact email is not configured: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Contact is temporarily unavailable. Please try again later.",
        ) from exc
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Contact email delivery failed")
        raise HTTPException(
            status_code=503,
            detail="Your message could not be sent. Please try again later.",
        ) from exc
    return {"reference": reference}
