from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)

from app.bot.service import run_bot

router = APIRouter()

small_webrtc_handler = SmallWebRTCRequestHandler()


@router.post("/offer")
async def offer(request: SmallWebRTCRequest, background_tasks: BackgroundTasks):
    """Handle WebRTC offer requests via SmallWebRTCRequestHandler."""

    async def webrtc_connection_callback(connection):
        background_tasks.add_task(run_bot, connection)

    answer = await small_webrtc_handler.handle_web_request(
        request=request,
        webrtc_connection_callback=webrtc_connection_callback,
    )
    return answer


@router.patch("/offer")
async def ice_candidate(request: SmallWebRTCPatchRequest):
    """Handle ICE candidate patches for WebRTC connections."""
    logger.debug(f"Received patch request: {request}")
    await small_webrtc_handler.handle_patch_request(request)
    return {"status": "success"}
