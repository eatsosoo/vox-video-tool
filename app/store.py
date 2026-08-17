import json
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
        return Project.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[Project]:
        return sorted((self.get(p.parent.name) for p in self.root.glob("*/project.json")), key=lambda x: x.id, reverse=True)

