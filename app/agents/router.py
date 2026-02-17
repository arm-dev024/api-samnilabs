from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.users.models import User
from app.agents.schemas import AgentCreate, AgentUpdate, AgentResponse
from app.agents.service import AgentService

router = APIRouter()


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
