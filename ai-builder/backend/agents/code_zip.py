"""In-memory ZIP builder for generated project files."""

import io
import zipfile

from models.schemas import GeneratedFile


def build_project_zip(files: list[GeneratedFile], archive_name: str = "project") -> bytes:
    """Build a ZIP archive preserving folder structure."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        written = 0
        for file in files:
            if file.path.endswith("/"):
                continue
            if file.content and file.content.strip():
                zf.writestr(file.path, file.content)
                written += 1
        if written == 0:
            zf.writestr(f"{archive_name}/.gitkeep", "")
    buffer.seek(0)
    return buffer.getvalue()
