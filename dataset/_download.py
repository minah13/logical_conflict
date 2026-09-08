"""공용 다운로드-후-캐시 유틸리티.

두 데이터셋 모두 공개 저장소(GitHub raw / Hugging Face resolve)에서 인증 없이
받을 수 있으므로, 사용자가 파일을 직접 내려받아 관리할 필요가 없도록
로컬 캐시 경로에 한 번만 다운로드해 재사용한다.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

DEFAULT_CACHE_ROOT = Path(__file__).resolve().parent.parent / "data"


def ensure_downloaded(url: str, cache_path: str | Path, force: bool = False) -> Path:
    """cache_path에 파일이 없으면(또는 force=True면) url에서 내려받아 저장한다."""

    cache_path = Path(cache_path)
    if force or not cache_path.exists():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".part")
        print(f"[download] {url} -> {cache_path}")
        urllib.request.urlretrieve(url, tmp_path)
        tmp_path.replace(cache_path)
    return cache_path
