from pathlib import Path

import pandas as pd
from typing import Dict


class InMemoryDataBridge:
    # 2단계 중첩 딕셔너리 구조: { dataset_id: { source_id: DataFrame } }
    _storage: Dict[str, Dict[str, pd.DataFrame]] = {}

    @classmethod
    def register(cls, dataset_id: str, source_id: str, df: pd.DataFrame):
        """특정 데이터셋 컨텍스트 내부에 안전하게 데이터프레임 등록"""
        if dataset_id not in cls._storage:
            cls._storage[dataset_id] = {}

        cls._storage[dataset_id][source_id] = df
        # logger.info(f"[Bridge] Registered data for DID: {dataset_id}, SRC: {source_id}")

    @classmethod
    def get(cls, dataset_id: str, source_id: str) -> pd.DataFrame:
        """지정된 데이터셋 내부의 격리된 소스 데이터만 반환"""
        if dataset_id not in cls._storage or source_id not in cls._storage[dataset_id]:
            raise KeyError(f"데이터를 찾을 수 없습니다. (DID: {dataset_id}, SRC: {source_id})")
        return cls._storage[dataset_id][source_id]

    @classmethod
    def clear_dataset(cls, dataset_id: str):
        """요청 처리가 끝난 데이터셋 영역을 통째로 날려 메모리 누수 방지"""
        cls._storage.pop(dataset_id, None)
        # if cls._storage.pop(dataset_id, None) is not None:
        #     logger.info(f"[Bridge] Cleaned up all cached data for DID: {dataset_id}")

    @classmethod
    def export_staging(cls, dataset_id: str, staging_dir: Path) -> None:
        """exec worker hydrate — ``{source_id}.parquet`` 로 control-side bridge 스냅샷."""
        frames = cls._storage.get(dataset_id)
        if not frames:
            return
        staging_dir.mkdir(parents=True, exist_ok=True)
        for source_id, df in frames.items():
            df.to_parquet(staging_dir / f"{source_id}.parquet", index=False)

    @classmethod
    def import_staging(cls, dataset_id: str, staging_dir: Path) -> None:
        """bind mount ``data/{did}/.bridge/`` → worker-side InMemoryDataBridge."""
        if not staging_dir.is_dir():
            return
        for path in staging_dir.glob("*.parquet"):
            cls.register(dataset_id, path.stem, pd.read_parquet(path))
