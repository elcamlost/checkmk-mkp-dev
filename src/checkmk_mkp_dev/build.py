import io
import json
import shutil
import tarfile
import tempfile
from pathlib import Path


def _make_category_tar(category_dir: Path) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", dereference=True) as tar:
        for path in sorted(category_dir.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=str(path.relative_to(category_dir)))
    return category_dir.name, buf.getvalue()


def _collect_files(staging: Path) -> dict[str, list[str]]:
    files = {}
    for category_dir in sorted(p for p in staging.iterdir() if p.is_dir()):
        files[category_dir.name] = sorted(
            str(p.relative_to(category_dir)) for p in category_dir.rglob("*") if p.is_file()
        )
    return files


def build_mkp(
    source: Path,
    output: Path,
    name: str,
    title: str,
    author: str,
    description: str,
    download_url: str,
    version: str,
    min_version: str,
) -> None:
    """Build a Checkmk MKP package from a directory of plugin files.

    Args:
        source: Directory containing the MKP file structure (top-level subdirs become categories).
        output: Path to write the resulting .mkp file.
        name: Package name (e.g. "telegram_notify").
        title: Human-readable title.
        author: Author string.
        description: Package description.
        download_url: URL for the package homepage.
        version: Package version string (e.g. "2.0.0").
        min_version: Minimum Checkmk version required (e.g. "2.3.0").
    """
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "stage"
        shutil.copytree(source, staging, ignore=ignore)

        files = _collect_files(staging)
        info = {
            "author": author,
            "description": description,
            "download_url": download_url,
            "files": files,
            "name": name,
            "num_files": sum(len(v) for v in files.values()),
            "title": title,
            "version": version,
            "version.min_required": min_version,
            "version.packaged": min_version,
            "version.usable_until": None,
        }
        categories = [_make_category_tar(d) for d in sorted(staging.iterdir()) if d.is_dir()]

        with tarfile.open(output, "w:gz") as mkp:
            for cat_name, data in categories:
                ti = tarfile.TarInfo(name=f"{cat_name}.tar")
                ti.size = len(data)
                mkp.addfile(ti, io.BytesIO(data))

            for filename, content in (
                ("info", repr(info).encode()),
                ("info.json", json.dumps(info).encode()),
            ):
                ti = tarfile.TarInfo(name=filename)
                ti.size = len(content)
                mkp.addfile(ti, io.BytesIO(content))
