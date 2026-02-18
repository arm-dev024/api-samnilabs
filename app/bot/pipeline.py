from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger
from openai import AsyncOpenAI
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


async def _generate_greeting(description: str, model: str = "gpt-4o-mini") -> str:
    """Use OpenAI to generate a brief opening greeting based on the assistant description."""
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Based on this assistant's description:\n\n{description}\n\n"
                    "Generate a brief 1-2 sentence opening greeting this assistant would say "
                    "when a user first connects. Return only the greeting text, nothing else."
                ),
            }
        ],
        max_tokens=80,
    )
    text = response.choices[0].message.content
    return (text or "").strip() or "Hello! How can I help you today?"


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

END_CALL_FUNCTION = FunctionSchema(
    name="end_call",
    description="End the call and disconnect. Use this when the conversation is complete, e.g. after confirming an appointment, user says goodbye, or the request has been fulfilled.",
    properties={},
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
    greeting_description: str | None = (
        None  # Used for greeting generation; falls back to system_prompt if unset
    )


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
            "content": (
                f"{config.system_prompt}\n\n"
                "If you hear background noise or non-human sounds, ignore them. "
                "Only respond to clear human speech."
            ),
        },
    ]

    task_ref: list = []  # Mutable ref for task, set after creation

    standard_tools: list = [END_CALL_FUNCTION]
    if config.calendar_id:
        standard_tools = [GET_AVAILABLE_DATE_TIME_FUNCTION, END_CALL_FUNCTION]

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

        llm.register_direct_function(
            get_available_date_time, cancel_on_interruption=False
        )

    async def end_call(params: FunctionCallParams) -> None:
        """End the call and disconnect when the conversation is complete."""
        await params.result_callback({"status": "ended"})
        if task_ref:
            await task_ref[0].cancel()

    llm.register_direct_function(end_call, cancel_on_interruption=False)

    tools = ToolsSchema(standard_tools=standard_tools)
    context = LLMContext(messages, tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
            user_idle_timeout=10.0,  # 20 seconds of silence before ending the call; TODO: Make this configurable
        ),
    )

    @user_aggregator.event_handler("on_user_turn_idle")
    async def on_user_idle(aggregator):
        """End the call when the user has been idle (no speech) for 10 seconds."""
        logger.info(f"User idle for 10s, ending call [{config.label}]")
        if task_ref:
            await task_ref[0].cancel()

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
    task_ref.append(task)

    @pipecat_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Pipecat client connected [{config.label}]")
        try:
            context_for_greeting = config.greeting_description or config.system_prompt
            greeting = await _generate_greeting(
                context_for_greeting,
                model=config.model,
            )
            context.add_message(
                {
                    "role": "system",
                    "content": f"Say the following as your first message: {greeting}",
                }
            )
        except Exception as e:
            logger.warning(f"Greeting generation failed, using default: {e}")
            context.add_message(
                {
                    "role": "system",
                    "content": "Say hello and briefly introduce yourself.",
                }
            )
        await task.queue_frames([LLMRunFrame()])

    @pipecat_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Pipecat client disconnected [{config.label}]")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
