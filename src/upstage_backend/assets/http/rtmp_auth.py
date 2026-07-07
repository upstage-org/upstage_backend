# -*- coding: iso8859-15 -*-
"""
Publish authentication for the MediaMTX RTMP server (/root/streaming2).

MediaMTX (authMethod: http) POSTs a JSON payload here for every connection
it has not excluded via authHTTPExclude. Read/playback actions are excluded
in mediamtx.yml (audience playback is anonymous), so in practice only
"publish" reaches this endpoint; anything else is allowed through as a
no-op to keep the exclusion list and this endpoint independently safe.

A publisher must present the token produced by AssetService.resolve_sign():
    token  = "<ts>-<md5('/live/<file_location>-<ts>-<STREAM_KEY>')>"
passed either as ?token=<...> on the RTMP URL query (what the studio's
ingest panel emits) or in the RTMP password slot (OBS "Use authentication").
The stream key must also belong to an existing asset of type "stream".

One token-less exception: the in-container Opus mirror. MediaMTX's
runOnReady ffmpeg (see /root/streaming2/mediamtx.yml) republishes each
live/<key> feed as live/<key>-opus with the audio transcoded AAC→Opus so
WebRTC playback has sound. That republish arrives over MediaMTX's
container-internal RTSP listener, so MediaMTX reports the loopback ip —
which no external publisher can present (RTMP and WebRTC publishes carry
the client's real address, and the RTSP port is neither published by
docker-compose nor proxied by nginx). Such publishes are accepted when the
mirrored base key belongs to a real stream asset.
"""

import hashlib
import hmac
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict

from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.global_config import get_session
from upstage_backend.global_config.env import STREAM_KEY
from upstage_backend.global_config.logger import logger

router = APIRouter()

RTMP_PATH_PREFIX = "live/"
OPUS_MIRROR_SUFFIX = "-opus"
LOOPBACK_IPS = ("127.0.0.1", "::1")


class MtxAuthPayload(BaseModel):
    """Fields MediaMTX sends; unknown/new fields are ignored."""

    model_config = ConfigDict(extra="ignore")

    user: str = ""
    password: str = ""
    ip: str = ""
    action: str = ""
    path: str = ""
    protocol: str = ""
    id: str | None = None
    query: str = ""


def _extract_token(payload: MtxAuthPayload) -> str:
    token = parse_qs(payload.query).get("token", [""])[0]
    return token or payload.password


def _token_is_valid(key: str, token: str) -> bool:
    ts, sep, digest = token.partition("-")
    if not sep or not ts.isdigit():
        return False
    if int(ts) <= time.time():
        return False  # expired (resolve_sign signs now + STREAM_EXPIRY_DAYS)
    expected = hashlib.md5(f"/live/{key}-{ts}-{STREAM_KEY}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, digest)


@router.post("/api/rtmp/auth")
async def rtmp_auth(payload: MtxAuthPayload):
    if payload.action != "publish":
        return Response(status_code=204)

    if not STREAM_KEY:
        # Fail closed: without the shared secret every token is forgeable.
        logger.error("rtmp_auth: STREAM_KEY is not configured; refusing publish")
        raise HTTPException(status_code=503, detail="RTMP publishing not configured")

    if not payload.path.startswith(RTMP_PATH_PREFIX):
        raise HTTPException(status_code=401, detail="Unknown path")
    key = payload.path[len(RTMP_PATH_PREFIX) :]

    # In-container Opus mirror (loopback-only; see module docstring). Falls
    # through to normal token validation when it doesn't match, so a real
    # asset whose key happens to end in "-opus" still publishes normally.
    if payload.ip in LOOPBACK_IPS and key.endswith(OPUS_MIRROR_SUFFIX):
        base_key = key[: -len(OPUS_MIRROR_SUFFIX)]
        base_asset = (
            get_session().query(AssetModel).filter(AssetModel.file_location == base_key).first()
        )
        if (
            base_asset is not None
            and base_asset.asset_type
            and base_asset.asset_type.name == "stream"
        ):
            logger.info("rtmp_auth: accepted opus-mirror publish for {}", payload.path)
            return Response(status_code=204)

    token = _extract_token(payload)
    if not token or not _token_is_valid(key, token):
        logger.warning("rtmp_auth: rejected publish for {} from {}", payload.path, payload.ip)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    asset = get_session().query(AssetModel).filter(AssetModel.file_location == key).first()
    if asset is None or not asset.asset_type or asset.asset_type.name != "stream":
        logger.warning("rtmp_auth: no stream asset for key {}", key)
        raise HTTPException(status_code=401, detail="Unknown stream key")

    logger.info("rtmp_auth: accepted publish for {} from {}", payload.path, payload.ip)
    return Response(status_code=204)
