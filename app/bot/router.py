import httpx
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
from app.config import settings

router = APIRouter()


async def _fetch_cloudflare_ice_servers() -> list[RTCIceServer]:
    """Fetch TURN/STUN credentials from the Cloudflare API."""
    token = settings.cloudflare_turn_token.get_secret_value()
    key_id = settings.cloudflare_turn_key_id

    if not token or not key_id:
        logger.warning("Cloudflare TURN credentials not set, no ICE servers configured")
        return []

    url = f"https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate-ice-servers"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"ttl": 86400},
        )
        resp.raise_for_status()
        data = resp.json()

    servers: list[RTCIceServer] = []
    for entry in data.get("iceServers", []):
        urls = entry.get("urls", [])
        username = entry.get("username")
        credential = entry.get("credential")
        if username and credential:
            servers.append(RTCIceServer(urls=urls, username=username, credential=credential))
        else:
            servers.append(RTCIceServer(urls=urls))

    logger.info(f"Fetched {len(servers)} ICE server entries from Cloudflare")
    return servers


# Initialized lazily on first request
small_webrtc_handler: SmallWebRTCRequestHandler | None = None


async def _get_handler() -> SmallWebRTCRequestHandler:
    global small_webrtc_handler
    if small_webrtc_handler is None:
        ice_servers = await _fetch_cloudflare_ice_servers()
        small_webrtc_handler = SmallWebRTCRequestHandler(
            connection_mode=ConnectionMode.SINGLE,
            ice_servers=ice_servers,
        )
    return small_webrtc_handler


@router.post("/offer")
async def offer(request: SmallWebRTCRequest, background_tasks: BackgroundTasks):
    """Handle WebRTC offer requests via SmallWebRTCRequestHandler."""
    logger.info(f"Offer received pc_id={request.pc_id!r} type={request.type!r}")
    handler = await _get_handler()

    async def webrtc_connection_callback(connection):
        background_tasks.add_task(run_bot, connection)

    answer = await handler.handle_web_request(
        request=request,
        webrtc_connection_callback=webrtc_connection_callback,
    )
    return answer


@router.patch("/offer")
async def ice_candidate(request: SmallWebRTCPatchRequest):
    """Handle ICE candidate patches for WebRTC connections."""
    logger.debug(f"Received patch request: {request}")
    handler = await _get_handler()
    await handler.handle_patch_request(request)
    return {"status": "success"}
