"""Administrator-authorized agent enrollment routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from synapse_contracts.agents import AgentEnroll, AgentKeyRotate, AgentPage, AgentView

from synapse_api.auth import get_principal, require_admin
from synapse_api.config import Principal
from synapse_api.db import get_db
from synapse_api.enrollment import (
    enroll_agent,
    get_agent,
    list_agents,
    revoke_agent,
    rotate_agent_key,
)

router = APIRouter(tags=["agents"])


@router.post("/api/v1/targets/{target_id}/agents", response_model=AgentView, status_code=201)
def post_agent(
    target_id: UUID,
    body: AgentEnroll,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> AgentView:
    return enroll_agent(session, target_id, body, principal.actor)


@router.get("/api/v1/targets/{target_id}/agents", response_model=AgentPage)
def get_target_agents(
    target_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> AgentPage:
    return list_agents(session, target_id, limit, offset)


@router.get("/api/v1/agents/{agent_id}", response_model=AgentView)
def get_agent_by_id(
    agent_id: UUID,
    _principal: Principal = Depends(get_principal),
    session: Session = Depends(get_db),
) -> AgentView:
    return get_agent(session, agent_id)


@router.post("/api/v1/agents/{agent_id}/revocation", response_model=AgentView)
def post_agent_revocation(
    agent_id: UUID,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> AgentView:
    return revoke_agent(session, agent_id, principal.actor)


@router.post("/api/v1/agents/{agent_id}/rotation", response_model=AgentView)
def post_agent_rotation(
    agent_id: UUID,
    body: AgentKeyRotate,
    principal: Principal = Depends(require_admin),
    session: Session = Depends(get_db),
) -> AgentView:
    return rotate_agent_key(session, agent_id, body, principal.actor)
