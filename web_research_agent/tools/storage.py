import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from web_research_agent.config import OUTPUT_DIR

class StorageManager:
    def __init__(self, base_dir: Path = OUTPUT_DIR):
        self.base_dir = base_dir
        self.reports_dir = base_dir / "reports"
        self.traces_dir = base_dir / "traces"
        self.exports_dir = base_dir / "exports"
        self.html_dir = self.exports_dir / "html"
        self.pdf_dir = self.exports_dir / "pdf"
        self.json_dir = self.exports_dir / "json"
        self.benchmarks_dir = base_dir / "benchmarks"
        self.runtime_dir = base_dir / "runtime"
        self.index_path = base_dir / "report_index.json"

    def generate_report_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        existing = list(self.reports_dir.glob(f"RPT-{date_str}-*.md"))
        # Extract numbers to find true max and avoid collisions if files deleted
        nums = []
        for p in existing:
            try: nums.append(int(p.stem.split("-")[-1]))
            except: pass
        next_num = (max(nums) if nums else 0) + 1
        return f"RPT-{date_str}-{next_num:03d}"

    def save_artifact(self, report_id: str, artifact_type: str, content: Any, extension: str):
        filename = f"{report_id}.{extension}"

        target_dir = {
            "report": self.reports_dir,
            "trace": self.traces_dir,
            "html": self.html_dir,
            "pdf": self.pdf_dir,
            "json": self.json_dir,
            "benchmark": self.benchmarks_dir,
            "runtime": self.runtime_dir
        }.get(artifact_type, self.base_dir)

        path = target_dir / filename

        if extension == "json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
        else:
            mode = "wb" if extension == "pdf" else "w"
            encoding = None if extension == "pdf" else "utf-8"
            with open(path, mode, encoding=encoding) as f:
                f.write(content)

        # Update shortcuts
        latest_path = self.base_dir / f"latest_{artifact_type}.{extension}"
        if extension != "pdf":
            shutil.copy(path, latest_path)

        return str(path.relative_to(self.base_dir))

    def update_index(self, entry: Dict[str, Any]):
        index = []
        if self.index_path.exists():
            try:
                with open(self.index_path, "r") as f:
                    index = json.load(f)
            except: pass

        index.append(entry)

        with open(self.index_path, "w") as f:
            json.dump(index, f, indent=2)

    def get_history(self) -> List[Dict[str, Any]]:
        if not self.index_path.exists():
            return []
        with open(self.index_path, "r") as f:
            return json.load(f)

    def get_report_path(self, report_id: str) -> Optional[Path]:
        path = self.reports_dir / f"{report_id}.md"
        return path if path.exists() else None

storage = StorageManager()
