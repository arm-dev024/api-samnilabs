from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.base_llm import BaseOpenAILLMService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from app.calendar.service import CalendarService
from app.config import settings


def _calendar_user_id(calendar_id: str) -> str:
    """Extract user id from calendar_id. Supports 'calendar[userId]' or plain userId."""
    if calendar_id.startswith("calendar[") and calendar_id.endswith("]"):
        return calendar_id[9:-1]
    return calendar_id


GET_AVAILABLE_DATE_TIME_FUNCTION = FunctionSchema(
    name="get_available_date_time",
    description="Get available time slots for a given date. Checks the calendar and returns only slots that are not booked. If no date is provided, uses today's date.",
    properties={
        "date": {
            "type": "string",
            "description": "Date in YYYY-MM-DD format. Defaults to today if omitted.",
        },
    },
    required=[],
)


@dataclass
class PipelineConfig:
    """Configuration for a Pipecat voice pipeline."""

    system_prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 150
    voice_id: str = "aura-2-thalia-en"
    label: str = "bot"
    calendar_id: str | None = None  # When set, enables get_available_date_time tool


async def run_pipeline(webrtc_connection, config: PipelineConfig):
    """Build and run a Pipecat voice pipeline from the given config."""
    pipecat_transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_out_10ms_chunks=2,
        ),
    )

    stt = DeepgramSTTService(api_key=settings.deepgram_api_key.get_secret_value())

    tts = DeepgramTTSService(
        api_key=settings.deepgram_api_key.get_secret_value(),
        voice=config.voice_id,
    )

    llm = OpenAILLMService(
        api_key=settings.openai_api_key.get_secret_value(),
        model=config.model,
        params=BaseOpenAILLMService.InputParams(
            temperature=config.temperature,
            max_completion_tokens=config.max_tokens,
            frequency_penalty=0.5,
            presence_penalty=0.5,
        ),
    )

    messages = [
        {
            "role": "system",
            "content": config.system_prompt,
        },
    ]

    tools = None
    if config.calendar_id:
        tools = ToolsSchema(standard_tools=[GET_AVAILABLE_DATE_TIME_FUNCTION])

        async def get_available_date_time(
            params: FunctionCallParams,
            date: str | None = None,
        ) -> None:
            """Get available time slots for a date. Uses today if date omitted. Returns slots that are not booked.

            Args:
                params: Function call parameters from the LLM service.
                date: Date in YYYY-MM-DD format. Defaults to today if omitted.
            """
            if not date:
                date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            user_id = _calendar_user_id(config.calendar_id)
            svc = CalendarService()
            days = svc.get_availability(user_id, date, date)
            slots = days[0]["slots"] if days else []
            await params.result_callback({"date": date, "available_slots": slots})

        llm.register_direct_function(get_available_date_time, cancel_on_interruption=False)

    context = LLMContext(messages, tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline = Pipeline(
        [
            pipecat_transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            pipecat_transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @pipecat_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Pipecat client connected [{config.label}]")
        await task.queue_frames([LLMRunFrame()])

    @pipecat_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Pipecat client disconnected [{config.label}]")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
