import asyncio
import hashlib
import shutil
import subprocess
from pathlib import Path

import httpx

from app.config import settings
from app.models import Project, Scene


def media_duration(path: Path) -> float:
    if not shutil.which(settings.ffprobe_bin):
        raise RuntimeError("Không tìm thấy FFprobe; hãy đặt FFPROBE_BIN trong .env")
    proc = subprocess.run(
        [settings.ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "FFprobe không đọc được thời lượng audio")
    return float(proc.stdout.strip())


def _audio_link(data: object) -> str | None:
    if isinstance(data, dict):
        for key in ("audio_link", "audio_url", "url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        for value in data.values():
            found = _audio_link(value)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = _audio_link(value)
            if found:
                return found
    return None


def _request_id(data: dict) -> str | None:
    result = data.get("result")
    if isinstance(result, dict):
        value = result.get("request_id")
        if value:
            return str(value)
    value = data.get("request_id")
    return str(value) if value else None


async def _vbee_audio_url(client: httpx.AsyncClient, scene: Scene) -> str:
    headers = {"Authorization": f"Bearer {settings.vbee_api_key}", "Content-Type": "application/json"}
    payload = {
        "app_id": settings.vbee_app_id,
        "input_text": scene.narration,
        "voice_code": settings.vbee_voice_code,
        "audio_type": "mp3",
        "bitrate": 128,
        "speed_rate": 1.0,
        "response_type": "indirect",
        "callback_url": settings.vbee_callback_url,
    }
    response = await client.post(settings.vbee_api_url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    if data.get("status") == 0:
        raise RuntimeError(f"Vbee: {data.get('error_message') or data.get('error_code') or 'không tạo được audio'}")
    direct = _audio_link(data)
    if direct:
        return direct
    request_id = _request_id(data)
    if not request_id:
        raise RuntimeError("Vbee không trả về request_id")

    deadline = asyncio.get_running_loop().time() + settings.vbee_timeout_seconds
    result_url = f"{settings.vbee_api_url.rstrip('/')}/{request_id}/callback-result"
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(settings.vbee_poll_seconds)
        status_response = await client.get(result_url, headers=headers)
        if status_response.status_code in (404, 409, 425):
            continue
        status_response.raise_for_status()
        status_data = status_response.json()
        link = _audio_link(status_data)
        if link:
            return link
        serialized = str(status_data).upper()
        if "FAILURE" in serialized or "FAILED" in serialized:
            raise RuntimeError(f"Vbee xử lý audio thất bại cho scene {scene.id}")
    raise RuntimeError(f"Vbee timeout sau {settings.vbee_timeout_seconds}s cho scene {scene.id}")


async def _download(client: httpx.AsyncClient, url: str, destination: Path) -> None:
    response = await client.get(url)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)


async def synthesize_vbee(scene: Scene, destination: Path) -> Path:
    cache_key = hashlib.sha256(f"{settings.vbee_voice_code}|1.0|{scene.narration}".encode("utf-8")).hexdigest()
    cached = settings.data_dir / "cache" / "tts" / "vbee" / f"{cache_key}.mp3"
    if cached.exists():
        shutil.copyfile(cached, destination)
        return destination
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=20), follow_redirects=True) as client:
        url = await _vbee_audio_url(client, scene)
        await _download(client, url, cached)
    shutil.copyfile(cached, destination)
    return destination


async def prepare_audio(project: Project, folder: Path) -> dict[int, Path]:
    provider = settings.tts_provider.lower()
    if provider in ("", "demo", "none"):
        return {}
    if provider != "vbee":
        raise RuntimeError(f"TTS_PROVIDER không được hỗ trợ: {settings.tts_provider}")
    if not settings.vbee_api_key or not settings.vbee_app_id:
        raise RuntimeError("TTS_PROVIDER=vbee nhưng thiếu VBEE_API_KEY hoặc VBEE_APP_ID")

    audio_by_scene: dict[int, Path] = {}
    for scene in project.scenes:
        path = folder / f"voice_{scene.id:03}.mp3"
        await synthesize_vbee(scene, path)
        scene.duration = min(60.0, max(2.0, media_duration(path) + 0.35))
        audio_by_scene[scene.id] = path
    return audio_by_scene
