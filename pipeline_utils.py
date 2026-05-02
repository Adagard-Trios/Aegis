"""Shared dataset-loading helpers for every model pipeline under models/<slug>/.

Every pipeline's DataIngestion._load_dataframe() funnels through this module
so the download / cache / credential logic lives in one place. The contract:

  * `cache_dir(slug, sub)` returns models/<slug>/data/<sub>/, creating it.
  * `download_*` helpers are idempotent: skip work if cache is present.
  * `require_env` / `require_module` raise DatasetUnavailable with a hint
    string the user can act on (env var name, install command, registration
    URL).
  * `is_large_allowed()` reads MEDVERSE_FETCH_LARGE from env so PTB-XL etc.
    don't auto-download multi-gigabyte data on a developer laptop.

Pipelines import only what they need — keep this module's top-level
imports thin so missing optional deps (kaggle, datasets, wfdb, …) don't
break unrelated pipelines.
"""
from __future__ import annotations

import importlib
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# Repo root — anchor for models/<slug>/data/ regardless of cwd.
# This file lives at the repo root, so __file__'s directory is the repo root.
_REPO_ROOT = Path(__file__).resolve().parent


# ─── Errors ────────────────────────────────────────────────────────────────


class DatasetUnavailable(RuntimeError):
    """Raised when a pipeline can't fetch its dataset.

    Always carries a `hint` string telling the user what to do (set an env
    var, install a package, register at a URL, etc.).
    """

    def __init__(self, message: str, *, hint: str = ""):
        # Use ASCII arrow so the message survives Windows cp1252 console logging
        full = message if not hint else f"{message}\n-> {hint}"
        super().__init__(full)
        self.hint = hint


# ─── Paths + flags ─────────────────────────────────────────────────────────


def cache_dir(slug: str, sub: str = "") -> Path:
    """Return (and create) `models/<slug>/data/<sub>/`."""
    base = _REPO_ROOT / "models" / slug / "data"
    target = base / sub if sub else base
    target.mkdir(parents=True, exist_ok=True)
    return target


def is_large_allowed() -> bool:
    return (os.environ.get("MEDVERSE_FETCH_LARGE") or "").lower() in ("1", "true", "yes", "on")


def is_dir_nonempty(p: Path) -> bool:
    return p.is_dir() and any(p.iterdir())


# ─── Guards ────────────────────────────────────────────────────────────────


def require_env(*names: str, hint: str) -> dict:
    """Return {name: value} or raise DatasetUnavailable listing missing names."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise DatasetUnavailable(
            f"missing required environment variables: {', '.join(missing)}",
            hint=hint,
        )
    return {n: os.environ[n] for n in names}


def require_large(reason: str, dataset_name: str, size: str) -> None:
    """Gate on MEDVERSE_FETCH_LARGE."""
    if not is_large_allowed():
        raise DatasetUnavailable(
            f"{dataset_name} ({size}) is gated. {reason}",
            hint="export MEDVERSE_FETCH_LARGE=true && python main.py",
        )


def require_module(module: str, install_hint: str):
    """Lazy-import or raise."""
    try:
        return importlib.import_module(module)
    except ImportError as e:
        raise DatasetUnavailable(
            f"required Python package '{module}' is not installed: {e}",
            hint=install_hint,
        ) from e


# ─── HTTP / archive helpers ────────────────────────────────────────────────


def download_file(url: str, target: Path, *, chunk: int = 1 << 20) -> Path:
    """Idempotent HTTP download. Skips if `target` already exists with size > 0."""
    if target.exists() and target.stat().st_size > 0:
        logger.info(f"download_file: cache hit → {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    requests = require_module("requests", "pip install requests>=2.31")
    tqdm_mod = require_module("tqdm", "pip install tqdm>=4.66")
    tqdm = getattr(tqdm_mod, "tqdm")
    logger.info(f"download_file: GET {url}")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        tmp = target.with_suffix(target.suffix + ".part")
        with tmp.open("wb") as fh, tqdm(
            total=total, unit="B", unit_scale=True, desc=target.name
        ) as bar:
            for buf in r.iter_content(chunk_size=chunk):
                if not buf:
                    continue
                fh.write(buf)
                bar.update(len(buf))
        tmp.replace(target)
    return target


def unzip(archive: Path, target_dir: Path, *, flatten_top: bool = False) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as z:
        z.extractall(target_dir)
    if flatten_top:
        # If the zip wrapped everything in a single top-level dir, flatten it.
        children = [p for p in target_dir.iterdir() if not p.name.startswith(".")]
        if len(children) == 1 and children[0].is_dir():
            inner = children[0]
            for sub in inner.iterdir():
                shutil.move(str(sub), target_dir / sub.name)
            inner.rmdir()
    return target_dir


# ─── PhysioNet ─────────────────────────────────────────────────────────────


def download_physionet(records_url: str, target_dir: Path, *, paths: Optional[Iterable[str]] = None) -> Path:
    """Download a PhysioNet dataset directory to `target_dir`.

    `records_url` is the base URL like
    ``https://physionet.org/files/<dataset>/<version>/``.

    If `paths` is given, only those relative paths are fetched (useful for
    the small reference subsets). If `paths` is None we fetch everything in
    the directory listing — only call this with `is_large_allowed()` already
    checked by the caller.
    """
    requests = require_module("requests", "pip install requests>=2.31")
    if not records_url.endswith("/"):
        records_url += "/"

    target_dir.mkdir(parents=True, exist_ok=True)

    if paths is not None:
        for rel in paths:
            dst = target_dir / rel
            if dst.exists() and dst.stat().st_size > 0:
                continue
            url = records_url + rel
            download_file(url, dst)
        return target_dir

    # Recursive directory walk — uses the PhysioNet HTTPS index pages.
    # We rely on wfdb.io.dl_database for safety / correctness when available,
    # otherwise fall back to a simple HTML-link crawler.
    try:
        wfdb = importlib.import_module("wfdb")
        # records_url like https://physionet.org/files/<dataset>/<version>/
        # wfdb.dl_database wants the dataset slug
        marker = "/files/"
        if marker in records_url:
            slug_path = records_url.split(marker, 1)[1].rstrip("/")
            wfdb.dl_database(slug_path, str(target_dir), keep_subdirs=True)
            return target_dir
    except Exception as e:
        logger.warning(f"wfdb.dl_database failed ({e}); falling back to HTML crawler")

    # Fallback: parse the directory listing
    visited = set()
    queue = [records_url]
    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        rel = url[len(records_url):]
        try:
            html = requests.get(url, timeout=60).text
        except Exception as e:
            logger.warning(f"download_physionet: skip {url} ({e})")
            continue
        for line in html.splitlines():
            # Naive parse: <a href="foo">…</a>
            i = line.find('href="')
            if i < 0:
                continue
            j = line.find('"', i + 6)
            if j < 0:
                continue
            href = line[i + 6 : j]
            if href in ("../", "/", "") or href.startswith("?") or href.startswith("#"):
                continue
            child = url + href
            if href.endswith("/"):
                queue.append(child)
            else:
                dst = target_dir / (rel + href)
                if dst.exists() and dst.stat().st_size > 0:
                    continue
                try:
                    download_file(child, dst)
                except Exception as e:
                    logger.warning(f"download_physionet: skip {child} ({e})")
    return target_dir


# ─── Kaggle ────────────────────────────────────────────────────────────────


def download_kaggle_dataset(slug: str, target: Path, *, force: bool = False) -> Path:
    """Download + unzip a Kaggle dataset (e.g. 'kmader/skin-cancer-mnist-ham10000').

    Reads KAGGLE_USERNAME / KAGGLE_KEY from env. If `target` is already
    populated, returns immediately unless force=True.
    """
    if not force and is_dir_nonempty(target):
        logger.info(f"download_kaggle_dataset: cache hit → {target}")
        return target
    require_env(
        "KAGGLE_USERNAME",
        "KAGGLE_KEY",
        hint=(
            "Get a Kaggle API token at https://www.kaggle.com/settings/account "
            "(Account → 'Create New API Token'). Add KAGGLE_USERNAME and "
            "KAGGLE_KEY to your .env file."
        ),
    )
    kaggle = require_module(
        "kaggle.api.kaggle_api_extended",
        "pip install kaggle>=1.6",
    )
    api = kaggle.KaggleApi()
    api.authenticate()
    target.mkdir(parents=True, exist_ok=True)
    api.dataset_download_files(slug, path=str(target), unzip=True, quiet=False)
    return target


def download_kaggle_competition(competition: str, target: Path, *, force: bool = False) -> Path:
    if not force and is_dir_nonempty(target):
        return target
    require_env("KAGGLE_USERNAME", "KAGGLE_KEY", hint="see Kaggle hint above")
    kaggle = require_module("kaggle.api.kaggle_api_extended", "pip install kaggle>=1.6")
    api = kaggle.KaggleApi()
    api.authenticate()
    target.mkdir(parents=True, exist_ok=True)
    api.competition_download_files(competition, path=str(target), quiet=False)
    # Unzip whatever it dropped in
    for z in target.glob("*.zip"):
        unzip(z, target)
        z.unlink()
    return target


# ─── HuggingFace ───────────────────────────────────────────────────────────


def download_huggingface_dataset(repo_id: str, **kwargs):
    """`datasets.load_dataset(...)` wrapper that pre-checks HF_TOKEN."""
    datasets = require_module("datasets", "pip install datasets>=2.18")
    token = os.environ.get("HF_TOKEN")
    if token:
        kwargs.setdefault("token", token)
    return datasets.load_dataset(repo_id, **kwargs)


def download_huggingface_file(repo_id: str, filename: str, target: Path, *, repo_type: str = "model") -> Path:
    """`huggingface_hub.hf_hub_download` wrapper. Caches into `target`."""
    if target.exists() and target.stat().st_size > 0:
        return target
    hub = require_module("huggingface_hub", "pip install huggingface_hub>=0.21")
    target.parent.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("HF_TOKEN")
    path = hub.hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        repo_type=repo_type,
        local_dir=str(target.parent),
        token=token,
    )
    src = Path(path)
    if src.resolve() != target.resolve():
        shutil.copy(src, target)
    return target


# ─── Synapse ───────────────────────────────────────────────────────────────


def download_synapse_entity(entity_id: str, target: Path) -> Path:
    """Pull a Synapse entity (e.g. WearGait-PD `syn52540892`) into target."""
    if is_dir_nonempty(target):
        return target
    require_env(
        "SYNAPSE_AUTH_TOKEN",
        hint=(
            "Register at https://www.synapse.org/, then create a personal "
            "access token at https://www.synapse.org/Profile:Tokens with "
            "the View + Download scopes. Add SYNAPSE_AUTH_TOKEN to .env."
        ),
    )
    synapseclient = require_module("synapseclient", "pip install synapseclient>=4.0")
    syn = synapseclient.Synapse()
    syn.login(authToken=os.environ["SYNAPSE_AUTH_TOKEN"])
    target.mkdir(parents=True, exist_ok=True)
    syn.get(entity_id, downloadLocation=str(target))
    return target


__all__ = [
    "DatasetUnavailable",
    "cache_dir",
    "is_large_allowed",
    "is_dir_nonempty",
    "require_env",
    "require_large",
    "require_module",
    "download_file",
    "unzip",
    "download_physionet",
    "download_kaggle_dataset",
    "download_kaggle_competition",
    "download_huggingface_dataset",
    "download_huggingface_file",
    "download_synapse_entity",
]
