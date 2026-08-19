import inspect
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.audio import prepare_audio
from app.config import settings
from app.media import resolve_font_file, run
from app.models import Project, Scene
from app.visuals import render_scene


ProgressCallback = Callable[[str, int], Awaitable[None] | None]


def srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms//3600000:02}:{(ms//60000)%60:02}:{(ms//1000)%60:02},{ms%1000:03}"


def write_srt(scenes: list[Scene], path: Path) -> None:
    cursor = 0.0
    chunks = []
    for index, scene in enumerate(scenes, 1):
        chunks.append(f"{index}\n{srt_time(cursor)} --> {srt_time(cursor + scene.duration)}\n{scene.narration}\n")
        cursor += scene.duration
    path.write_text("\n".join(chunks), encoding="utf-8")


async def _notify(callback: ProgressCallback | None, status: str, progress: int) -> None:
    if not callback:
        return
    result = callback(status, progress)
    if inspect.isawaitable(result):
        await result


async def _concat_video(clips: list[Path], folder: Path) -> Path:
    concat = folder / "video_concat.txt"
    concat.write_text("\n".join(f"file '{clip.name}'" for clip in clips), encoding="utf-8")
    output = folder / "silent.mp4"
    await run(settings.ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output))
    return output


async def _concat_audio(project: Project, audio_by_scene: dict[int, Path], folder: Path) -> Path | None:
    if not audio_by_scene:
        return None
    normalized: list[Path] = []
    for scene in project.scenes:
        source = audio_by_scene[scene.id]
        output = folder / f"voice_normalized_{scene.id:03}.m4a"
        await run(
            settings.ffmpeg_bin, "-y", "-i", str(source),
            "-af", "loudnorm=I=-16:LRA=11:TP=-1.5,apad",
            "-t", str(scene.duration), "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", str(output),
        )
        normalized.append(output)
    concat = folder / "audio_concat.txt"
    concat.write_text("\n".join(f"file '{audio.name}'" for audio in normalized), encoding="utf-8")
    output = folder / "narration.m4a"
    await run(settings.ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output))
    return output


def _subtitle_filter(path: Path) -> str:
    subtitle_path = str(path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    style = "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101827,Outline=2,Shadow=0,MarginV=35,Alignment=2"
    selected_font = resolve_font_file()
    if selected_font:
        fonts_dir = str(selected_font.parent).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        return f"subtitles='{subtitle_path}':fontsdir='{fonts_dir}':force_style='{style}'"
    return f"subtitles='{subtitle_path}':force_style='{style}'"


async def _compose(project: Project, silent: Path, narration: Path | None, subtitles: Path, folder: Path) -> Path:
    output = folder / "final.mp4"
    duration = sum(scene.duration for scene in project.scenes)
    command = [settings.ffmpeg_bin, "-y", "-i", str(silent)]
    if narration:
        command.extend(["-i", str(narration)])

    music: Path | None = None
    if settings.background_music:
        music = Path(settings.background_music)
        if not music.exists():
            raise RuntimeError(f"Không tìm thấy BACKGROUND_MUSIC: {music}")
        command.extend(["-stream_loop", "-1", "-i", str(music)])

    command.extend(["-vf", _subtitle_filter(subtitles), "-map", "0:v:0"])
    if narration and music:
        command.extend([
            "-filter_complex", f"[1:a]volume=1[voice];[2:a]volume={settings.music_volume}[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "[aout]", "-c:a", "aac", "-b:a", "192k",
        ])
    elif narration:
        command.extend(["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"])
    elif music:
        command.extend(["-filter_complex", f"[1:a]volume={settings.music_volume}[aout]", "-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
    command.extend(["-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)])
    await run(*command)
    return output


async def render(project: Project, folder: Path, progress: ProgressCallback | None = None) -> Path:
    if not shutil.which(settings.ffmpeg_bin):
        raise RuntimeError("Không tìm thấy FFmpeg")
    folder.mkdir(parents=True, exist_ok=True)

    await _notify(progress, "generating_voice", 30)
    audio_by_scene = await prepare_audio(project, folder)

    await _notify(progress, "rendering_visuals", 55)
    clips: list[Path] = []
    total = max(1, len(project.scenes))
    for index, scene in enumerate(project.scenes):
        clip = folder / f"scene_{scene.id:03}.mp4"
        await render_scene(project, scene, clip)
        clips.append(clip)
        await _notify(progress, "rendering_visuals", 55 + round((index + 1) / total * 20))

    await _notify(progress, "composing", 82)
    silent = await _concat_video(clips, folder)
    narration = await _concat_audio(project, audio_by_scene, folder)
    subtitles = folder / "subtitles.srt"
    write_srt(project.scenes, subtitles)
    output = await _compose(project, silent, narration, subtitles, folder)
    await _notify(progress, "finalizing", 96)
    return output
