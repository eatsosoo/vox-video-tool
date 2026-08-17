import asyncio
import shutil
from pathlib import Path
from app.config import settings
from app.models import Project, Scene


def dimensions(ratio: str) -> tuple[int, int]:
    return {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080)}[ratio]


def srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms//3600000:02}:{(ms//60000)%60:02}:{(ms//1000)%60:02},{ms%1000:03}"


def write_srt(scenes: list[Scene], path: Path) -> None:
    cursor = 0.0
    chunks = []
    for i, scene in enumerate(scenes, 1):
        chunks.append(f"{i}\n{srt_time(cursor)} --> {srt_time(cursor + scene.duration)}\n{scene.narration}\n")
        cursor += scene.duration
    path.write_text("\n".join(chunks), encoding="utf-8")


async def run(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode:
        raise RuntimeError(err.decode(errors="replace")[-2000:])


async def render_demo(project: Project, folder: Path) -> Path:
    width, height = dimensions(project.request.aspect_ratio)
    clips = []
    colors = ["#172554", "#7c2d12", "#14532d", "#581c87", "#713f12"]
    for i, scene in enumerate(project.scenes):
        clip = folder / f"scene_{scene.id:03}.mp4"
        title = (scene.title or f"CẢNH {scene.id}").replace("'", "’").replace(":", "\\:")
        vf = f"drawtext=text='{title}':fontcolor=white:fontsize={max(28,width//22)}:x=(w-text_w)/2:y=(h-text_h)/2"
        await run(settings.ffmpeg_bin, "-y", "-f", "lavfi", "-i", f"color=c={colors[i%len(colors)]}:s={width}x{height}:r=30",
                  "-t", str(scene.duration), "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip))
        clips.append(clip)
    concat = folder / "concat.txt"
    concat.write_text("\n".join(f"file '{p.name}'" for p in clips), encoding="utf-8")
    silent = folder / "silent.mp4"
    await run(settings.ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent))
    srt = folder / "subtitles.srt"
    write_srt(project.scenes, srt)
    output = folder / "final.mp4"
    style = "FontName=DejaVu Sans,FontSize=18,Outline=2,Shadow=0,MarginV=35,Alignment=2"
    subtitle_path = str(srt.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    await run(settings.ffmpeg_bin, "-y", "-i", str(silent), "-vf", f"subtitles='{subtitle_path}':force_style='{style}'",
              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output))
    return output


async def render(project: Project, folder: Path) -> Path:
    if not shutil.which(settings.ffmpeg_bin):
        raise RuntimeError("Không tìm thấy FFmpeg")
    # Production adapters are deliberately isolated: FlowKit/Vbee can replace this renderer
    # without changing API, storage, scene schema, or UI.
    return await render_demo(project, folder)
