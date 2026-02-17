from pydantic import BaseModel


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""

    name: str
    description: str
    system_prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 150
    voice_provider: str = "deepgram"  # "deepgram" | "cartesia" | etc.
    voice_id: str = "aura-2-thalia-en"


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent."""

    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    voice_provider: str | None = None
    voice_id: str | None = None
    is_active: bool | None = None


class AgentResponse(BaseModel):
    """Public agent representation returned by the API."""

    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    voice_provider: str
    voice_id: str
    is_active: bool
    created_at: str
    updated_at: str
