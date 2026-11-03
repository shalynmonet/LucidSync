"""Hall–Van de Castle dream content coding models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CodingRow(BaseModel):
    """One evidence-backed content code; source_quote is verbatim dream text."""

    model_config = ConfigDict(extra="forbid")

    category: str
    code: str
    subject: str = ""
    related_to: str = ""
    source_quote: str
    rationale: str


class DreamCoding(BaseModel):
    """Structured coding table plus a non-diagnostic plain-language summary."""

    model_config = ConfigDict(extra="forbid")

    rows: list[CodingRow]
    summary: str

    @model_validator(mode="after")
    def require_evidence(self) -> "DreamCoding":
        for row in self.rows:
            if not row.source_quote.strip():
                raise ValueError("Every coding row must cite dream-report evidence.")
        return self
