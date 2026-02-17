from aiortc import RTCIceServer
from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pipecat.transports.smallwebrtc.request_handler import (
    ConnectionMode,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)

from app.bot.service import run_bot

router = APIRouter()

# SINGLE mode prevents duplicate server-side connections when the client
# sends a second offer (e.g. reconnection), avoiding two pipelines for one session.
small_webrtc_handler = SmallWebRTCRequestHandler(
    connection_mode=ConnectionMode.SINGLE,
    # ice_servers=[
    #     RTCIceServer(urls="stun:stun.l.google.com:19302"),
    # ],
)


@router.post("/offer")
async def offer(request: SmallWebRTCRequest, background_tasks: BackgroundTasks):
    """Handle WebRTC offer requests via SmallWebRTCRequestHandler."""
    logger.info(f"Offer received pc_id={request.pc_id!r} type={request.type!r}")

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
