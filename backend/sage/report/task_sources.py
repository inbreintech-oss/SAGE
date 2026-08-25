"""Report task executor disk paths — LLM/codegen 의존성 없음 (exec worker 공용)."""

from __future__ import annotations

from pathlib import Path

import cfg

REPORTS_DIR = Path(cfg.root_path) / "reports"


def report_dir(rid: str) -> Path:
    """보고서 자산 루트: reports/{rid}/"""
    return REPORTS_DIR / rid


def report_srcs_dir(rid: str) -> Path:
    """executor 소스 디렉터리 — generate 가 채우고 exec 가 읽는다."""
    return report_dir(rid) / "srcs"


def task_source_path(rid: str, task_id: str) -> Path:
    """태스크 executor 소스: reports/{rid}/srcs/{task_id}.py"""
    return report_srcs_dir(rid) / f"{task_id}.py"


def ensure_report_dirs(rid: str) -> Path:
    """rid 루트와 srcs/ 를 만들고 루트 Path 를 반환."""
    root = report_dir(rid)
    report_srcs_dir(rid).mkdir(parents=True, exist_ok=True)
    return root


def save_task_source(rid: str, task_id: str, code: str) -> Path:
    """validated 소스를 디스크에 기록 — 이후 run_task_code 가 이 파일만 본다."""
    path = task_source_path(rid, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    return path
