from aiortc import RTCIceServer
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from pipecat.transports.smallwebrtc.request_handler import (
    ConnectionMode,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)

from app.auth.dependencies import get_current_user
from app.users.models import User
from app.agents.playground import run_agent_playground
from app.agents.schemas import AgentCreate, AgentUpdate, AgentResponse
from app.agents.service import AgentService

router = APIRouter()

playground_webrtc_handler = SmallWebRTCRequestHandler(
    connection_mode=ConnectionMode.SINGLE,
    ice_servers=[
        RTCIceServer(urls="stun:stun.l.google.com:19302"),
    ],
)


@router.post("/", response_model=AgentResponse, status_code=201)
def create_agent(
    data: AgentCreate,
    user: User = Depends(get_current_user),
):
    service = AgentService()
    agent = service.create_agent(user, data)
    return AgentService.build_agent_response(agent)


@router.get("/", response_model=list[AgentResponse])
def list_agents(
    user: User = Depends(get_current_user),
):
    service = AgentService()
    agents = service.list_agents(user)
    return [AgentService.build_agent_response(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
):
    service = AgentService()
    agent = service.get_agent(user, agent_id)
    return AgentService.build_agent_response(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    data: AgentUpdate,
    user: User = Depends(get_current_user),
):
    service = AgentService()
    agent = service.update_agent(user, agent_id, data)
    return AgentService.build_agent_response(agent)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
):
    service = AgentService()
    service.delete_agent(user, agent_id)


# ── Agent Playground (WebRTC) ──────────────────────────────────────


@router.post("/{agent_id}/playground/offer")
async def playground_offer(
    agent_id: str,
    request: SmallWebRTCRequest,
    background_tasks: BackgroundTasks,
):
    """Start a WebRTC playground session using the agent's configuration."""
    service = AgentService()
    agent = service.get_agent_by_id(agent_id)

    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active",
        )

    logger.info(f"Playground offer for agent={agent_id}")

    async def webrtc_connection_callback(connection):
        background_tasks.add_task(run_agent_playground, connection, agent)

    answer = await playground_webrtc_handler.handle_web_request(
        request=request,
        webrtc_connection_callback=webrtc_connection_callback,
    )
    return answer


@router.patch("/{agent_id}/playground/offer")
async def playground_ice_candidate(
    agent_id: str,
    request: SmallWebRTCPatchRequest,
):
    """Handle ICE candidate patches for playground WebRTC connections."""
    logger.debug(f"Playground patch for agent={agent_id}")
    await playground_webrtc_handler.handle_patch_request(request)
    return {"status": "success"}
