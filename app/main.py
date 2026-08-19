import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.director import create_scenes
from app.models import Project, ProjectRequest
from app.render import render
from app.store import ProjectStore

app = FastAPI(title="VOX Video Tool", version="0.1.0")
store = ProjectStore(settings.data_dir / "projects")


async def process(project_id: str):
    project = store.get(project_id)
    try:
        project.status, project.progress = "planning", 15
        store.save(project)
        project.scenes = await create_scenes(project.request)
        project.status, project.progress = "planned", 20
        store.save(project)
        folder = settings.data_dir / "projects" / project.id

        async def update_progress(status: str, progress: int):
            project.status, project.progress = status, progress
            store.save(project)

        output = await render(project, folder, update_progress)
        project.status, project.progress = "completed", 100
        project.output_url = f"/api/projects/{project.id}/video"
        store.save(project)
    except Exception as exc:
        detail = str(exc).strip() or f"{type(exc).__name__}: lỗi không có thông báo"
        project.status, project.error = "failed", detail
        store.save(project)


@app.post("/api/projects", response_model=Project, status_code=202)
async def create_project(req: ProjectRequest):
    config_errors = [] if settings.is_demo else settings.production_errors()
    if config_errors:
        raise HTTPException(503, "Cấu hình production chưa hoàn tất: " + "; ".join(config_errors))
    project = Project(
        id=uuid.uuid4().hex[:12],
        status="queued",
        created_at=datetime.now(timezone.utc),
        request=req,
    )
    store.save(project)
    asyncio.create_task(process(project.id))
    return project


@app.get("/api/projects", response_model=list[Project])
def list_projects():
    return store.list()


@app.get("/api/config")
def get_config():
    return {
        "app_mode": settings.app_mode,
        "openai_model": settings.openai_model,
        "tts_provider": settings.tts_provider,
        "visual_provider": settings.visual_provider,
        "ready": settings.is_demo or not settings.production_errors(),
        "errors": [] if settings.is_demo else settings.production_errors(),
    }


@app.get("/api/projects/{project_id}", response_model=Project)
def get_project(project_id: str):
    project = store.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@app.get("/api/projects/{project_id}/video")
def get_video(project_id: str):
    path = settings.data_dir / "projects" / project_id / "final.mp4"
    if not path.exists():
        raise HTTPException(404, "Video not ready")
    return FileResponse(path, media_type="video/mp4", filename=f"vox-{project_id}.mp4")


static = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static, html=True), name="static")
