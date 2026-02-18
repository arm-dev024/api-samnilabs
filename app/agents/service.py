from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.agents.models import Agent
from app.agents.schemas import AgentCreate, AgentUpdate, AgentResponse
from app.users.models import User
from app.users.repository import UserRepository


class AgentService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()

    def create_agent(self, user: User, data: AgentCreate) -> Agent:
        agent = Agent(
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            model=data.model,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            voice_provider=data.voice_provider,
            voice_id=data.voice_id,
            calendar_id=data.calendar_id,
        )
        user.agents.append(agent)
        self.user_repo.update(user)
        return agent

    def list_agents(self, user: User) -> list[Agent]:
        return user.agents

    def get_agent(self, user: User, agent_id: str) -> Agent:
        for agent in user.agents:
            if agent.id == agent_id:
                return agent
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    def update_agent(self, user: User, agent_id: str, data: AgentUpdate) -> Agent:
        agent = self.get_agent(user, agent_id)

        if data.name is not None:
            agent.name = data.name
        if data.description is not None:
            agent.description = data.description
        if data.system_prompt is not None:
            agent.system_prompt = data.system_prompt
        if data.model is not None:
            agent.model = data.model
        if data.temperature is not None:
            agent.temperature = data.temperature
        if data.max_tokens is not None:
            agent.max_tokens = data.max_tokens
        if data.voice_provider is not None:
            agent.voice_provider = data.voice_provider
        if data.voice_id is not None:
            agent.voice_id = data.voice_id
        if data.is_active is not None:
            agent.is_active = data.is_active
        if "calendar_id" in data.model_fields_set:
            agent.calendar_id = data.calendar_id

        agent.updated_at = datetime.now(timezone.utc).isoformat()
        self.user_repo.update(user)
        return agent

    def delete_agent(self, user: User, agent_id: str) -> None:
        agent = self.get_agent(user, agent_id)
        user.agents.remove(agent)
        self.user_repo.update(user)

    def get_agent_by_id(self, agent_id: str) -> Agent:
        """Find an agent by ID across all users (for public/playground access)."""
        table = self.user_repo.table
        response = table.scan(
            FilterExpression="attribute_exists(agents)",
        )
        for item in response.get("Items", []):
            user = User.from_dynamo_item(item)
            for agent in user.agents:
                if agent.id == agent_id:
                    return agent
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    @staticmethod
    def build_agent_response(agent: Agent) -> AgentResponse:
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            system_prompt=agent.system_prompt,
            model=agent.model,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            voice_provider=agent.voice_provider,
            voice_id=agent.voice_id,
            is_active=agent.is_active,
            calendar_id=agent.calendar_id,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
