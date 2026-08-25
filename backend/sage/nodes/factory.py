"""NodeFactory — repo-root nodes/ catalog loader."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict

import cfg
from sage.logg import error

from sage.nodes.framework import NodeV

class NodeFactory:
    """
    nodes/ 하위의 계층적 폴더 구조를 지원하는 노드 팩토리.
    예: nodes['report/plan'] -> {nodes_path}/report/plan/main.py
    """

    def __init__(self) -> None:
        self.nodes_base_dir = Path(cfg.nodes_path)
        self._cache: Dict[str, Any] = {}

    def __getitem__(self, node_path_key: str) -> NodeV:
        # 노드 인스턴스는 프로세스당 1회 생성 (instruction/validated 경로 캐시)
        if node_path_key in self._cache:
            return self._cache[node_path_key]

        target_dir = self.nodes_base_dir.joinpath(*node_path_key.split("/"))
        main_py_path = target_dir / "main.py"

        if not main_py_path.exists():
            raise ValueError(f"노드 실행 파일을 찾을 수 없습니다: {node_path_key}")

        # 동일 path 재import 충돌 방지 — sage.nodes.gen_report_plan 형식
        module_unique_name = f"sage.nodes.gen_{node_path_key.replace('/', '_')}"

        try:
            spec = importlib.util.spec_from_file_location(module_unique_name, main_py_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Spec 생성 실패: {node_path_key}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_unique_name] = module
            spec.loader.exec_module(module)

            node_class = None
            # main.py 내 @node 데코레이터가 붙은 NodeV 서브클래스 1개를 탐색
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (
                    isinstance(attr, type)
                    and issubclass(attr, NodeV)
                    and attr is not NodeV
                    and hasattr(attr, "__node_input_model__")
                ):
                    node_class = attr
                    break

            if not node_class:
                raise AttributeError(
                    f"'{main_py_path}'에 @node 로 정의된 NodeV 클래스가 없습니다."
                )

            instance = node_class()
            self._cache[node_path_key] = instance
            return instance

        except Exception as e:
            error(f"Node 로딩 중 오류 발생 [{node_path_key}]: {str(e)}")
            raise e

nodes = NodeFactory()
