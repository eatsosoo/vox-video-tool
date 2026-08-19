import shlex
from pathlib import Path

from app.config import settings
from app.media import dimensions, escape_drawtext, resolve_font_file, run
from app.models import Project, Scene, SceneType


COLORS = {
    SceneType.cinematic: ("#07111f", "#f5c84c"),
    SceneType.infographic: ("#102a43", "#2dd4bf"),
    SceneType.chart: ("#172554", "#fb7185"),
    SceneType.map: ("#14342b", "#facc15"),
    SceneType.archive: ("#292524", "#e7e5e4"),
}


def _font_option() -> str:
    selected = resolve_font_file()
    if not selected:
        return ""
    path = escape_drawtext(str(selected))
    return f"fontfile='{path}':"


def _local_filter(scene: Scene, width: int, height: int) -> tuple[str, str]:
    background, accent = COLORS[scene.scene_type]
    font = _font_option()
    filters = [
        f"drawbox=x=0:y=0:w=iw:h={max(8, height // 80)}:color={accent}:t=fill",
        f"drawbox=x={width // 14}:y={height // 9}:w={width // 5}:h=4:color={accent}:t=fill",
    ]
    if scene.scene_type == SceneType.chart:
        baseline = int(height * 0.76)
        for index, ratio in enumerate((0.25, 0.42, 0.62, 0.82)):
            bar_height = int(height * ratio * 0.55)
            filters.append(f"drawbox=x={int(width * (0.16 + index * 0.18))}:y={baseline - bar_height}:w={int(width * 0.1)}:h={bar_height}:color={accent}@0.82:t=fill")
    elif scene.scene_type == SceneType.infographic:
        for index in range(3):
            filters.append(f"drawbox=x={int(width * (0.12 + index * 0.29))}:y={int(height * 0.58)}:w={int(width * 0.2)}:h={int(height * 0.16)}:color={accent}@{0.35 + index * 0.18}:t=fill")
    elif scene.scene_type == SceneType.map:
        filters.extend(["drawgrid=w=96:h=96:t=1:c=white@0.08", f"drawbox=x={int(width * 0.58)}:y={int(height * 0.32)}:w={int(width * 0.18)}:h={int(height * 0.22)}:color={accent}@0.65:t=fill"])
    elif scene.scene_type == SceneType.archive:
        filters.extend(["noise=alls=7:allf=t+u", "eq=saturation=0.35:contrast=1.08"])
    else:
        filters.append("vignette=PI/5")

    title = escape_drawtext(scene.title or scene.overlay_text or f"CẢNH {scene.id}")
    subtitle = escape_drawtext(scene.subtitle or scene.overlay_text)
    filters.append(
        f"drawtext={font}text='{title}':expansion=none:fontcolor=white:fontsize={max(30, width // 24)}:"
        f"x={width // 14}:y={height // 4}:borderw=2:bordercolor=black@0.35"
    )
    if subtitle and subtitle != title:
        filters.append(
            f"drawtext={font}text='{subtitle}':expansion=none:fontcolor={accent}:fontsize={max(22, width // 38)}:"
            f"x={width // 14}:y={int(height * 0.43)}:borderw=1:bordercolor=black@0.35"
        )
    filters.extend([
        f"drawtext={font}text='{scene.scene_type.value.upper()} / {scene.id:02}':expansion=none:fontcolor=white@0.65:fontsize={max(16, width // 60)}:x={width // 14}:y=h-{height // 10}",
        "fade=t=in:st=0:d=0.35",
        f"fade=t=out:st={max(0.0, scene.duration - 0.35):.3f}:d=0.35",
    ])
    return ",".join(filters), background


async def render_local_scene(project: Project, scene: Scene, output: Path) -> None:
    width, height = dimensions(project.request.aspect_ratio)
    video_filter, background = _local_filter(scene, width, height)
    await run(
        settings.ffmpeg_bin, "-y", "-f", "lavfi", "-i", f"color=c={background}:s={width}x{height}:r=30",
        "-t", str(scene.duration), "-vf", video_filter, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output),
    )


async def render_flowkit_scene(project: Project, scene: Scene, output: Path) -> None:
    if not settings.flowkit_command:
        raise RuntimeError("VISUAL_PROVIDER=flowkit nhưng thiếu FLOWKIT_COMMAND")
    raw = output.with_name(f"{output.stem}_provider.mp4")
    command = shlex.split(settings.flowkit_command)
    command.extend([
        "--prompt", scene.visual_prompt,
        "--duration", str(scene.duration),
        "--aspect-ratio", project.request.aspect_ratio,
        "--output", str(raw),
    ])
    await run(*command)
    if not raw.exists():
        raise RuntimeError(f"FlowKit wrapper không tạo file: {raw}")
    width, height = dimensions(project.request.aspect_ratio)
    await run(
        settings.ffmpeg_bin, "-y", "-i", str(raw), "-t", str(scene.duration),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output),
    )


async def render_scene(project: Project, scene: Scene, output: Path) -> None:
    provider = settings.visual_provider.lower()
    if provider not in ("local", "flowkit"):
        raise RuntimeError(f"VISUAL_PROVIDER không được hỗ trợ: {settings.visual_provider}")
    if provider == "flowkit" and scene.scene_type == SceneType.cinematic:
        await render_flowkit_scene(project, scene, output)
    else:
        await render_local_scene(project, scene, output)
