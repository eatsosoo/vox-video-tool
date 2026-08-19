from pathlib import Path
from app.audio import _audio_link
from app.director import SCENE_SCHEMA, demo_scenes
from app.models import Project, ProjectRequest
from app.render import srt_time, write_srt
from app.store import ProjectStore


def test_demo_scene_schema(tmp_path: Path):
    req = ProjectRequest(topic="Máy bán hàng tự động", target_seconds=30)
    scenes = demo_scenes(req)
    assert scenes and scenes[0].id == 1
    assert "no text" in scenes[0].visual_prompt
    path = tmp_path / "x.srt"
    write_srt(scenes, path)
    assert "-->" in path.read_text(encoding="utf-8")


def test_srt_time():
    assert srt_time(65.123) == "00:01:05,123"


def test_director_uses_object_scene_schema():
    assert SCENE_SCHEMA["type"] == "object"
    assert SCENE_SCHEMA["properties"]["scenes"]["items"]["additionalProperties"] is False


def test_nested_vbee_audio_link():
    payload = {"result": {"payload": {"audio_link": "https://cdn.example.test/voice.mp3"}}}
    assert _audio_link(payload) == "https://cdn.example.test/voice.mp3"


def test_store_adds_created_at_to_legacy_project(tmp_path: Path):
    store = ProjectStore(tmp_path)
    project = Project(id="legacy", status="completed", request=ProjectRequest(topic="Dự án cũ"))
    store.save(project)

    loaded = store.get("legacy")

    assert loaded is not None
    assert loaded.created_at is not None
