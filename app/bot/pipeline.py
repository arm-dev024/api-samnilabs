from dataclasses import dataclass

from loguru import logger
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
from pipecat.services.openai.base_llm import BaseOpenAILLMService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from app.config import settings


@dataclass
class PipelineConfig:
    """Configuration for a Pipecat voice pipeline."""

    system_prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 150
    voice_id: str = "aura-2-thalia-en"
    label: str = "bot"


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

    context = LLMContext(messages)
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
