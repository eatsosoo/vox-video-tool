import asyncio
import uuid
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
        project.status, project.progress = "rendering", 55
        store.save(project)
        folder = settings.data_dir / "projects" / project.id
        output = await render(project, folder)
        project.status, project.progress = "completed", 100
        project.output_url = f"/api/projects/{project.id}/video"
        store.save(project)
    except Exception as exc:
        project.status, project.error = "failed", str(exc)
        store.save(project)


@app.post("/api/projects", response_model=Project, status_code=202)
async def create_project(req: ProjectRequest):
    project = Project(id=uuid.uuid4().hex[:12], status="queued", request=req)
    store.save(project)
    asyncio.create_task(process(project.id))
    return project


@app.get("/api/projects", response_model=list[Project])
def list_projects():
    return store.list()


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

