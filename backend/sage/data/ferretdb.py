from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import re
import pandas as pd

import cfg

async def load_data(
        did: str,
        version: str = "latest",  # 기본값을 latest로 변경
        columns: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    물리적 저장소(Storage)의 Parquet 파일로부터 데이터를 로드합니다.
    version이 'latest'인 경우 가장 최신 버전을 자동으로 탐색합니다.
    """
    try:
        base_path = Path(cfg.root_path)
        pangea_root = base_path / "data" / did / "pangea"

        if not pangea_root.exists():
            raise FileNotFoundError(f"Pangea root not found: {pangea_root}")

        # 1. 'latest' 버전 처리
        target_version = version
        if version == "latest":
            # 폴더 목록 중 'v'로 시작하고 숫자가 붙은 폴더 추출 (예: v1, v2, v10)
            version_dirs = [
                d.name for d in pangea_root.iterdir()
                if d.is_dir() and re.match(r'^v\d+$', d.name)
            ]

            if not version_dirs:
                raise FileNotFoundError(f"No version folders found in {pangea_root}")

            # 버전 숫자 기준 정렬 (v10이 v2보다 뒤에 오도록 숫자로 추출하여 비교)
            target_version = sorted(
                version_dirs,
                key=lambda x: int(re.sub(r'\D', '', x)),
                reverse=True
            )[0]

        target_path = pangea_root / target_version / "data.parquet"

        if not target_path.exists():
            raise FileNotFoundError(f"Data file not found: {target_path}")

        # 2. 데이터 로드 및 변환 (Pydantic 규격을 위해 ensure_ascii=False 정책 고려)
        df = pd.read_parquet(target_path, columns=columns, engine='pyarrow')

        # 3. Pandas의 numpy 타입을 순수 Python 타입으로 변환 (직렬화 안전성)
        result_data = df.to_dict(orient='records')

        metadata = {
            "did": did,
            "version": target_version,
            "requested_version": version,
            "row_count": len(df)
        }

        return result_data, metadata

    except Exception as e:
        print(f"[StorageLoadError] {did}/{version}: {e}")
        raise e
