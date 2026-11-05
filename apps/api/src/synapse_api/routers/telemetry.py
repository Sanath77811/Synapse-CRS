"""Telemetry ingestion routes. Agents authenticate with a detached signature."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from synapse_contracts.telemetry_ingest import TelemetryIngestRequest, TelemetryIngestView

from synapse_api.db import get_db
from synapse_api.ingest import ingest_telemetry

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


@router.post("/ingest", response_model=TelemetryIngestView)
def post_ingest(
    body: TelemetryIngestRequest,
    session: Session = Depends(get_db),
) -> TelemetryIngestView | JSONResponse:
    result = ingest_telemetry(session, body)
    if result.status_code in {200, 201}:
        return JSONResponse(status_code=result.status_code, content=result.body)
    return JSONResponse(status_code=result.status_code, content=result.body)
