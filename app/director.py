import json
import re
import httpx
from app.config import settings
from app.models import ProjectRequest, Scene, SceneType


SYSTEM = """Bạn là đạo diễn video explainer. Trả về duy nhất JSON array. Mỗi phần tử gồm:
id, duration (2-12), narration, scene_type (cinematic|infographic|map|chart|archive),
visual_prompt (English, include 'no text, no letters, no watermark'), title, subtitle.
Không yêu cầu model video vẽ chữ; chữ Việt chỉ nằm trong title/subtitle. Tổng duration gần mục tiêu."""


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
                  title=req.topic if i == 0 else "", subtitle="") for i, s in enumerate(parts)]


async def create_scenes(req: ProjectRequest) -> list[Scene]:
    if settings.app_mode == "demo" or not settings.openai_api_key:
        return demo_scenes(req)
    prompt = f"Chủ đề: {req.topic}\nScript: {req.script or '(hãy tự viết)'}\nThời lượng: {req.target_seconds}s\nNgôn ngữ: {req.language}"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    payload = {"model": settings.openai_model, "input": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
    raw = data.get("output_text") or next(c["text"] for o in data["output"] for c in o.get("content", []) if c.get("type") == "output_text")
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return [Scene.model_validate(x) for x in json.loads(raw)]

