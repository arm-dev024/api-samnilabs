from datetime import datetime

from app.agents.models import Agent
from app.bot.pipeline import PipelineConfig, run_pipeline


async def run_agent_playground(webrtc_connection, agent: Agent):
    """Run a Pipecat pipeline configured from the agent's settings."""
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")

    config = PipelineConfig(
        system_prompt=(
            f"{agent.system_prompt}\n\n"
            f"Current date and time: {current_datetime}."
        ),
        model=agent.model,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        voice_id=agent.voice_id,
        label=f"playground:{agent.id}",
    )

    await run_pipeline(webrtc_connection, config)
