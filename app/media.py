import asyncio
import os
import subprocess
from pathlib import Path

from app.config import settings


def dimensions(ratio: str) -> tuple[int, int]:
    return {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080)}[ratio]


def run_sync(args: tuple[str, ...]) -> None:
    proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        detail = proc.stderr.decode(errors="replace").strip()[-4000:]
        raise RuntimeError(detail or f"Tiến trình kết thúc với mã lỗi {proc.returncode}")


async def run(*args: str) -> None:
    await asyncio.to_thread(run_sync, args)


def escape_drawtext(value: str) -> str:
    return value.replace("\\", "/").replace("'", "’").replace(":", "\\:").replace("\n", " ")


def resolve_font_file() -> Path | None:
    if settings.font_file:
        configured = Path(settings.font_file)
        if not configured.exists():
            raise RuntimeError(f"Không tìm thấy FONT_FILE: {configured}")
        return configured.resolve()
    if os.name == "nt":
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("arial.ttf", "segoeui.ttf", "tahoma.ttf"):
            candidate = fonts / name
            if candidate.exists():
                return candidate.resolve()
    return None
