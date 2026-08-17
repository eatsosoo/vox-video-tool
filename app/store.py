import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from app.models import Project


class ProjectStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

    def save(self, project: Project) -> None:
        folder = self.root / project.id
        folder.mkdir(parents=True, exist_ok=True)
        with self.lock:
            (folder / "project.json").write_text(project.model_dump_json(indent=2), encoding="utf-8")

    def get(self, project_id: str) -> Project | None:
        path = self.root / project_id / "project.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        # Older projects did not store created_at. On Windows, ctime is the
        # file creation time and gives those projects a useful fallback.
        if not data.get("created_at"):
            data["created_at"] = datetime.fromtimestamp(path.stat().st_ctime, timezone.utc).isoformat()
        return Project.model_validate(data)

    def list(self) -> list[Project]:
        projects = (self.get(p.parent.name) for p in self.root.glob("*/project.json"))
        return sorted(projects, key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
