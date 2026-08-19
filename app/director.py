import json
import re
import httpx
from app.config import settings
from app.models import ProjectRequest, Scene, SceneType


SYSTEM = """Bạn là đạo diễn video explainer editorial, lấy cảm hứng từ ngôn ngữ kể chuyện dữ liệu hiện đại. Trả về kế hoạch scene theo schema được cung cấp. Mỗi scene gồm:
id, duration (2-12), narration, scene_type (cinematic|infographic|map|chart|archive),
visual_prompt (English, include 'no text, no letters, no watermark'), title, subtitle,
overlay_text, source_query, transition và camera_motion.
Viết narration tiếng Việt tự nhiên, chính xác, câu ngắn. Không yêu cầu model video vẽ chữ;
chữ Việt chỉ nằm trong title/subtitle/overlay_text. Tổng duration gần mục tiêu."""


SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "duration": {"type": "number", "minimum": 2, "maximum": 12},
                    "narration": {"type": "string"},
                    "scene_type": {"type": "string", "enum": ["cinematic", "infographic", "map", "chart", "archive"]},
                    "visual_prompt": {"type": "string"},
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "overlay_text": {"type": "string"},
                    "source_query": {"type": "string"},
                    "transition": {"type": "string"},
                    "camera_motion": {"type": "string"},
                },
                "required": ["id", "duration", "narration", "scene_type", "visual_prompt", "title", "subtitle", "overlay_text", "source_query", "transition", "camera_motion"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["scenes"],
    "additionalProperties": False,
}


def _sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?。])\s+|\n+", text) if x.strip()]


def demo_scenes(req: ProjectRequest) -> list[Scene]:
    text = req.script.strip() or (
        f"{req.topic} là một chủ đề đáng tìm hiểu. "
        "Trước tiên, chúng ta nhìn vào bối cảnh và những mốc quan trọng. "
        "Tiếp theo, các dữ kiện cho thấy nhiều yếu tố cùng tác động. "
        "Cuối cùng, điều quan trọng là kiểm chứng nguồn và nhìn vấn đề từ nhiều phía."
    )
    parts = _sentences(text)
    duration = max(3.0, min(8.0, req.target_seconds / max(len(parts), 1)))
    kinds = [SceneType.cinematic, SceneType.infographic, SceneType.chart, SceneType.archive]
    return [Scene(id=i + 1, duration=duration, narration=s, scene_type=kinds[i % len(kinds)],
                  visual_prompt=f"Editorial documentary visual about {req.topic}, paper collage, bold geometric shapes, no text, no letters, no watermark",
                  title=req.topic if i == 0 else "", subtitle="", overlay_text="",
                  source_query=f"{req.topic} scene {i + 1}", transition="fade",
                  camera_motion="slow_zoom_in") for i, s in enumerate(parts)]


async def create_scenes(req: ProjectRequest) -> list[Scene]:
    if settings.is_demo:
        return demo_scenes(req)
    if not settings.openai_api_key:
        raise RuntimeError("Thiếu OPENAI_API_KEY trong chế độ production")
    prompt = f"Chủ đề: {req.topic}\nScript: {req.script or '(hãy tự viết)'}\nThời lượng: {req.target_seconds}s\nNgôn ngữ: {req.language}"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.openai_model,
        "input": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "text": {"format": {"type": "json_schema", "name": "vox_scene_plan", "strict": True, "schema": SCENE_SCHEMA}},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
    raw = data.get("output_text") or next(c["text"] for o in data["output"] for c in o.get("content", []) if c.get("type") == "output_text")
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(raw)
    return [Scene.model_validate(x) for x in parsed["scenes"]]
