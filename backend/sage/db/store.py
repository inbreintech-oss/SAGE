"""MongoDB async document store (Motor) for SAGE domain models."""

import atexit
import json
import os
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, Union

import motor.motor_asyncio
import numpy as np
from pydantic import BaseModel, TypeAdapter

from sage.logg import error
from sage.models import doc
from sage.models.doc import ReportStatus

# --- 전역 직렬화 도구 설정 ---
ANY_ADAPTER = TypeAdapter(Any)


def load_db_settings() -> tuple[str, str]:
    """DB 접속 설정 — backend 교체 시에도 동일 env 키 사용."""
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("SAGE_DB_NAME", "sage_db")
    return uri, db_name


class DocumentBackend(ABC):
    """문서 DB 비동기 접근 — Mongo 외 클라우드 DB 로 교체 시 구현체만 교체."""

    @abstractmethod
    def collection(self, name: str): ...

    @abstractmethod
    async def replace_one(self, collection: str, doc_id: str, data: dict) -> None: ...

    @abstractmethod
    async def find_one(self, collection: str, filter: dict, *, sort: list | None = None) -> dict | None: ...

    @abstractmethod
    async def find_many(
            self,
            collection: str,
            filter: dict,
            *,
            limit: int | None = None,
            sort: list | None = None,
    ) -> list[dict]: ...

    @abstractmethod
    async def update_one(self, collection: str, filter: dict, update: dict): ...

    @abstractmethod
    async def delete_one(self, collection: str, doc_id: str) -> int: ...

    @abstractmethod
    async def delete_many(self, collection: str, filter: dict) -> int: ...

    @abstractmethod
    async def update_many(self, collection: str, filter: dict, update: dict): ...

    @abstractmethod
    def find_one_sync(self, collection: str, filter: dict) -> dict | None: ...


def _unregister_pymongo_atexit() -> None:
    """명시적 close 후 pymongo atexit join — Ctrl+C 시 KeyboardInterrupt 노이즈 방지."""
    try:
        from pymongo.synchronous.monitor import _shutdown_resources

        atexit.unregister(_shutdown_resources)
    except Exception:
        pass


class MongoDocumentBackend(DocumentBackend):
    """Motor(async) + PyMongo(sync read) — 기본 MongoDB 구현."""

    def __init__(self, uri: str | None = None, db_name: str | None = None):
        default_uri, default_db = load_db_settings()
        self.uri = uri or default_uri
        self.db_name = db_name or default_db
        self._async_client = motor.motor_asyncio.AsyncIOMotorClient(self.uri)
        self._sync_client = None
        self._closed = False

    @property
    def db(self):
        return self._async_client[self.db_name]

    def _sync_db(self):
        if self._sync_client is None:
            from pymongo import MongoClient

            self._sync_client = MongoClient(self.uri)
        return self._sync_client[self.db_name]

    def collection(self, name: str):
        return self.db[name]

    async def replace_one(self, collection: str, doc_id: str, data: dict) -> None:
        await self.db[collection].replace_one({"_id": doc_id}, data, upsert=True)

    async def find_one(self, collection: str, filter: dict, *, sort: list | None = None) -> dict | None:
        kwargs = {"sort": sort} if sort else {}
        return await self.db[collection].find_one(filter, **kwargs)

    async def find_many(
            self,
            collection: str,
            filter: dict,
            *,
            limit: int | None = None,
            sort: list | None = None,
    ) -> list[dict]:
        cursor = self.db[collection].find(filter)
        if sort:
            cursor = cursor.sort(sort)
        if limit is not None:
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=limit or None)

    async def update_one(self, collection: str, filter: dict, update: dict):
        return await self.db[collection].update_one(filter, update)

    async def delete_one(self, collection: str, doc_id: str) -> int:
        result = await self.db[collection].delete_one({"_id": doc_id})
        return result.deleted_count

    async def delete_many(self, collection: str, filter: dict) -> int:
        result = await self.db[collection].delete_many(filter)
        return result.deleted_count

    async def update_many(self, collection: str, filter: dict, update: dict):
        return await self.db[collection].update_many(filter, update)

    def find_one_sync(self, collection: str, filter: dict) -> dict | None:
        return self._sync_db()[collection].find_one(filter)

    def close(self) -> None:
        """프로세스 종료 전 호출 — pymongo atexit KeyboardInterrupt 노이즈 방지."""
        if self._closed:
            return
        self._closed = True
        if self._sync_client is not None:
            try:
                self._sync_client.close()
            except Exception:
                pass
            self._sync_client = None
        try:
            self._async_client.close()
        except Exception:
            pass
        _unregister_pymongo_atexit()


class SyncDBWrapper:
    """동기 read wrapper — MCP 도구 runtime 등. backend 교체 시 DocumentBackend.find_one_sync 만 수정."""

    def __init__(self, store: "SAGEDataStore"):
        self._store = store

    def get_by_id(self, collection: str, doc_id: str) -> dict | None:
        raw = self._store._backend.find_one_sync(collection, {"_id": doc_id})
        return self._store._read(raw) if raw else None


def convert_numpy_types(obj: Any) -> Any:
    """객체 내부의 NumPy 타입을 표준 Python 타입으로 재귀적으로 변환합니다."""
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return [convert_numpy_types(i) for i in obj.tolist()]
    if isinstance(obj, dict):
        return {
            (k.item() if isinstance(k, np.generic) else str(k)): convert_numpy_types(v)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple, set)):
        return [convert_numpy_types(i) for i in obj]
    return obj


def universal_serializer(obj: Any) -> Any:
    """NumPy 처리 후 Pydantic v2를 사용하여 JSON 호환 타입으로 변환합니다."""
    converted = convert_numpy_types(obj)
    # Pydantic 모델인 경우 dump_python을, 일반 객체인 경우 그대로 반환하거나 변환
    if isinstance(converted, BaseModel):
        return converted.model_dump(mode='python')
    return ANY_ADAPTER.dump_python(converted, mode='python')


class SAGEDataStore:
    """Async MongoDB document store with prefix-based collection routing."""

    def __init__(
            self,
            uri: str | None = None,
            db_name: str | None = None,
            backend: DocumentBackend | None = None,
    ):
        default_uri, default_db = load_db_settings()
        self._backend = backend or MongoDocumentBackend(uri or default_uri, db_name or default_db)
        self.db = self._backend.db
        # self._sync = SyncDBWrapper(self)

        # ------------------------------------------------------------------
        # _config_map 접두사 라우팅
        # - 도메인 문서 _id 가 "rp-xxx", "did-yyy" 처럼 접두사를 갖는 관례를
        #   이용해, 호출자가 컬렉션명을 몰라도 get/save/delete 가 동작하게 함.
        # - 값: [Mongo 컬렉션명, Pydantic 모델] — did- 만 모델 None
        #   (데이터셋은 스키마가 유동적이라 raw dict + put 사용).
        # - 새 도메인 추가 시 여기만 등록하면 save/load/list_all_ids 전부에 연결.
        # ------------------------------------------------------------------
        # [통합 설정 맵] 접두사: [컬렉션명, 모델클래스]
        self._config_map = {
            "rp-": ["reports", doc.Report],
            "pl-": ["plans", doc.Plan],
            "task-": ["tasks", doc.Task],
            "sk-": ["secrets", doc.SecretKey],
            "tm-": ["tools", doc.Tool],
            "exec-": ["executions", doc.Execution],
            "sess-": ["sessions", doc.Session],
            "did-": ["data", None],
            "log-": ["logs", doc.Log]
        }

        # 역방향: model_class → collection (save(doc.Report(...)) 시 사용)
        self._class_to_col = {
            conf[1]: conf[0] for conf in self._config_map.values() if conf[1] is not None
        }

        # __getattr__ 허용 집합 — saged.reports 같은 속성 접근 화이트리스트.
        self._valid_collections = {conf[0] for conf in self._config_map.values()}
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        close = getattr(self._backend, "close", None)
        if callable(close):
            close()

    # @property
    # def sync(self) -> SyncDBWrapper:
    #     return self._sync

    def __getattr__(self, name: str):
        """
        saged.reports 형태로 접근 시 self.db["reports"]를 반환합니다.
        """
        if name in self._valid_collections:
            return self.db[name]

        # 정의되지 않은 컬렉션 접근 시 기본 에러 발생
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _encode_nested_lists(self, data: Any) -> Any:
        """중첩 리스트를 찾아 JSON 문자열로 변환하여 MongoDB 제약을 우회합니다."""
        # MongoDB 는 nested array 인덱싱/일부 연산에 제약이 있어,
        # [[...]] 형태를 JSON 문자열로 접어 넣고 읽을 때 펼친다.
        if isinstance(data, list):
            if any(isinstance(i, list) for i in data):
                return json.dumps(data)
            return [self._encode_nested_lists(i) for i in data]
        if isinstance(data, dict):
            return {k: self._encode_nested_lists(v) for k, v in data.items()}
        return data

    def _decode_nested_lists(self, data: Any) -> Any:
        """저장된 JSON 문자열을 원래의 리스트 구조로 복원합니다."""
        # 휴리스틱: '['...']' 문자열만 시도. encode 와 쌍을 이룸.
        if isinstance(data, str) and data.startswith('[') and data.endswith(']'):
            try:
                return json.loads(data)
            except:
                return data
        if isinstance(data, list):
            return [self._decode_nested_lists(i) for i in data]
        if isinstance(data, dict):
            return {k: self._decode_nested_lists(v) for k, v in data.items()}
        return data

    def _sanitize_mongodb_keys(self, obj: Any) -> Any:
        """MongoDB 저장 시 에러를 유발하는 키($로 시작하는 키)를 재귀적으로 변환합니다."""
        # '$' 키는 update operator 와 충돌 → '_$' 접두로 이스케이프.
        if isinstance(obj, dict):
            return {
                (f"_{k}" if isinstance(k, str) and k.startswith('$') else k):
                    self._sanitize_mongodb_keys(v)
                for k, v in obj.items()
            }
        if isinstance(obj, (list, tuple)):
            return [self._sanitize_mongodb_keys(i) for i in obj]
        return obj

    def _restore_mongodb_keys(self, obj: Any) -> Any:
        """MongoDB에서 읽어온 데이터의 변환된 키(_$로 시작하는 키)를 원래대로($) 복구합니다."""
        # sanitize 의 역: '_$or' → '$or' 등. 앱/LLM 이 원래 JSON Schema 키를 보게.
        if isinstance(obj, dict):
            return {
                (k[1:] if isinstance(k, str) and k.startswith('_$') else k):
                    self._restore_mongodb_keys(v)
                for k, v in obj.items()
            }
        if isinstance(obj, (list, tuple)):
            return [self._restore_mongodb_keys(i) for i in obj]
        return obj

    def _read(self, doc_data: Any) -> Any:
        """조회된 모든 데이터에 대해 공통적으로 수행할 후처리 로직 (키 복구 및 JSON 리스트 복원)"""
        # encode/sanitize 파이프라인의 읽기 쪽 대칭:
        # restore keys → decode nested lists. 모든 get/list/load 가 여기를 통과.
        if doc_data is None:
            return None
        restored = self._restore_mongodb_keys(doc_data)
        return self._decode_nested_lists(restored)

    def _collection_name(self, target: Union[Type[BaseModel], str]) -> str:
        """Pydantic 클래스 또는 ID 접두사(rp-, did-, tm- …) → Mongo 컬렉션명."""
        # 클래스 → 맵 직행; 문자열이면 첫 '-' 까지를 접두사로 추출.
        if target in self._class_to_col:
            return self._class_to_col[target]

        if isinstance(target, str):
            idx = target.find('-')
            prefix = target[:idx + 1] if idx != -1 else target
            config = self._config_map.get(prefix)
            if config:
                return config[0]
            # exec- 변형 호환 (옛 id 관례)
            if prefix.startswith('exec'):
                return "executions"

        raise ValueError(f"Mapping not found for target: {target}")

    def get_collection(self, target: Union[Type[BaseModel], str]):
        """클래스 타입 또는 ID 문자열을 받아 적절한 컬렉션을 반환합니다."""
        return self.db[self._collection_name(target)]

    # --- Write Operations ---
    # encode/sanitize 파이프라인 (쓰기):
    #   universal_serializer|numpy → _encode_nested_lists → _sanitize_mongodb_keys
    #   → replace_one(upsert)
    # 읽기는 _read 가 역순에 가깝게 restore → decode.
    async def save(self, model: BaseModel):
        """Pydantic 모델 인스턴스를 받아 NumPy/MongoDB 제약을 처리 후 저장합니다."""
        # ------------------------------------------------------------------
        # save vs put
        # - save: 타입이 고정된 도메인 문서(Report, Tool, …). 모델 dump 후
        #   "첫 필드"(rid/tool_id/…)를 _id 로 복제. 호출부는 모델만 넘기면 됨.
        # - put: did 데이터셋처럼 스키마가 유동적인 raw dict. 호출부가
        #   이미 _id 를 넣고, 모델 검증 없이 그대로 영속.
        # 둘 다 replace_one upsert — insert/update API 를 하나로 통일.
        # ------------------------------------------------------------------
        raw_data = universal_serializer(model)

        # 중첩 리스트 직렬화 -> MongoDB 키 정제 순으로 진행
        data = self._encode_nested_lists(raw_data)
        data = self._sanitize_mongodb_keys(data)

        # 첫 번째 필드 값을 _id로 사용 (모델 필드 선언 순서에 의존하는 관례).
        first_key = list(data.keys())[0]
        _id = data[first_key]
        data["_id"] = _id
        data["updated_at"] = datetime.now(timezone.utc)

        col_name = self._collection_name(model.__class__)
        try:
            return await self._backend.replace_one(col_name, _id, data)
        except Exception as e:
            traceback.print_exc()
            raise e

    async def put(self, data: Dict[str, Any]):
        """Raw 딕셔너리 데이터를 정제하여 저장합니다."""
        # Pydantic 없이 저장 — pangeaze 의 did 문서 등.
        # _id 필수: 접두사 라우팅과 Mongo primary key 를 동시에 만족.
        if "_id" not in data:
            raise ValueError("Data must contain '_id' field")

        clean_data = convert_numpy_types(data)
        clean_data = self._encode_nested_lists(clean_data)
        clean_data = self._sanitize_mongodb_keys(clean_data)

        col_name = self._collection_name(clean_data["_id"])
        clean_data["updated_at"] = datetime.now(timezone.utc)
        return await self._backend.replace_one(col_name, clean_data["_id"], clean_data)

    # --- Read Operations ---
    # get: dict + _read 후처리 / load: get 후 model_validate
    # list_all: 문서 전체(limit) / list_all_ids: 삭제 배치용 id 목록

    async def get(self, _id: str) -> Optional[Dict[str, Any]]:
        """ID로 단일 문서를 조회하고 후처리합니다."""
        # 접두사로 컬렉션을 고르므로 호출자는 컬렉션명을 몰라도 됨.
        col_name = self._collection_name(_id)
        doc_data = await self._backend.find_one(col_name, {"_id": _id})
        return self._read(doc_data)

    async def load(self, model_class: Type[BaseModel], _id: str) -> Optional[Any]:
        """조회된 데이터를 모델로 변환합니다."""
        # get 과의 차이: 타입 안전 API. 스키마 깨진 문서는 ValidationError.
        doc_data = await self.get(_id)
        return model_class.model_validate(doc_data) if doc_data else None

    async def get_execution(self, task_id: str) -> Optional[Dict[str, Any]]:
        """최신 Execution 기록을 조회하고 후처리합니다."""
        # 같은 task 에 Execution 이 여러 번 쌓이므로 updated_at 내림차순 1건.
        doc_data = await self._backend.find_one(
            "executions",
            {"target_id": task_id},
            sort=[("updated_at", -1)],
        )
        return self._read(doc_data)

    async def list_all(self, prefix: str, limit: int = 100):
        """특정 도메인의 데이터를 최신순으로 조회하고 후처리합니다."""
        # prefix("rp-" 등) → 컬렉션 전체 스캔. 목록 UI/디버그용.
        # 각 문서에 _read 적용해 앱이 보는 키/리스트 형태를 일치시킴.
        try:
            col_name = self._collection_name(prefix)
            docs = await self._backend.find_many(
                col_name,
                {},
                limit=limit,
                sort=[("updated_at", -1)],
            )
            return [self._read(doc) for doc in docs]
        except Exception as e:
            print(f"list_all 오류: {e}")
            return []

    async def list_all_ids(self, target: Union[Type[BaseModel], str]) -> List[str]:
        """
        지정한 컬렉션에 존재하는 모든 문서의 _id 목록을 최신순으로 조회합니다.

        :param target: 모델 클래스(예: doc.Report), ID 접두사(예: 'rp-'), 또는 컬렉션명(예: 'reports')
        """
        # 일괄 삭제(all/exclude) 가 본문 없이 id 만 필요할 때 사용.
        # (주석의 projection 최적화는 향후 여지 — 현재는 find_many 후 _id 추출)
        try:
            # SAGEDataStore 내부 매핑 로직을 그대로 통과시켜 올바른 컬렉션명을 얻습니다.
            col_name = self._collection_name(target)

            # 대량의 데이터 처리 시 부하를 줄이기 위해 프로젝션으로 _id만 가볍게 추출합니다.
            docs = await self._backend.find_many(
                col_name,
                {},
                sort=[("updated_at", -1)]
            )
            return [doc["_id"] for doc in docs if "_id" in doc]
        except Exception as e:
            print(f"get_all_ids 오류 (target: {target}): {e}")
            return []

    # --- Delete Operations ---

    async def delete(self, _id: str) -> bool:
        """단일 문서를 삭제합니다."""
        try:
            col_name = self._collection_name(_id)
            deleted = await self._backend.delete_one(col_name, _id)
            return deleted > 0
        except Exception as e:
            print(f"delete 오류 ({_id}): {e}")
            return False

    async def delete_many(self, model_class: Type[BaseModel], filter_dict: dict) -> int:
        """
        특정 모델 클래스에 해당하는 컬렉션에서 조건에 맞는 데이터를 대량 삭제합니다.
        예: await db.delete_many(doc.Execution, {"rid": rid})
        """
        try:
            col_name = self._collection_name(model_class)
            return await self._backend.delete_many(col_name, filter_dict)
        except Exception as e:
            print(f"delete_many 오류 ({model_class.__name__}): {e}")
            return 0

    async def update_report_status(self, rid: str, status: ReportStatus):
        """리포트 전용 상태 업데이트 단축 함수"""
        col_name = self._collection_name(rid)
        return await self._backend.update_one(
            col_name,
            {"_id": rid},
            {"$set": {"status": status.lower(), "updated_at": datetime.now(timezone.utc)}},
        )

    # --- SecretKey ---

    async def list_secrets(self, user_id: str = "admin") -> List[doc.SecretKey]:
        raw_docs = await self._backend.find_many("secrets", {"user_id": user_id})
        return [doc.SecretKey.model_validate(self._read(d)) for d in raw_docs]

    async def load_secret_by_provider(
        self, user_id: str, provider: str,
    ) -> Optional[doc.SecretKey]:
        raw = await self._backend.find_one(
            "secrets",
            {"user_id": user_id, "provider": provider},
        )
        return doc.SecretKey.model_validate(self._read(raw)) if raw else None

    def load_secret_by_provider_sync(
        self, user_id: str, provider: str,
    ) -> Optional[Dict[str, Any]]:
        raw = self._backend.find_one_sync(
            "secrets",
            {"user_id": user_id, "provider": provider},
        )
        return self._read(raw) if raw else None

    async def list_secrets_by_names(self, user_id: str, key_names: list[str]) -> List[doc.SecretKey]:
        from sage.secret.crypto import normalize_key_name

        names = {normalize_key_name(k) for k in key_names if k and k.strip()}
        if not names:
            return []
        out: list[doc.SecretKey] = []
        for record in await self.list_secrets(user_id):
            if any(item.key_name in names for item in record.keys):
                out.append(record)
        return out

    async def load_secret(self, user_id: str, key_name: str) -> Optional[doc.SecretKey]:
        from sage.secret.crypto import normalize_key_name

        name = normalize_key_name(key_name)
        for record in await self.list_secrets(user_id):
            if any(item.key_name == name for item in record.keys):
                return record
        return None

    def load_secret_sync(self, user_id: str, key_name: str) -> Optional[Dict[str, Any]]:
        from sage.secret.crypto import normalize_key_name

        name = normalize_key_name(key_name)
        backend = self._backend
        if not hasattr(backend, "_sync_db"):
            return None
        for raw in backend._sync_db()["secrets"].find({"user_id": user_id}):
            doc_data = self._read(raw)
            keys = doc_data.get("keys") or []
            if any(k.get("key_name") == name for k in keys):
                return doc_data
        return None


async def migrate_collection_field(prefix: str, old_key: str, new_key: str):
    """
    특정 컬렉션(prefix로 식별)의 모든 문서에서 old_key를 new_key로 변경합니다.

    Args:
        prefix (str): 'rp-', 'pl-', 'exec-' 등 SAGEDataStore 매핑용 접두사
        old_key (str): 변경 전 필드명 (예: 'rid')
        new_key (str): 변경 후 필드명 (예: 'id')
    """
    try:
        col_name = saged._collection_name(prefix)
        result = await saged._backend.update_many(
            col_name,
            {old_key: {"$exists": True}},
            {"$rename": {old_key: new_key}},
        )

        print(f"[{col_name}] 컬렉션 마이그레이션 완료")
        print(f"- 대상 문서 수: {result.matched_count}")
        print(f"- 변경 문서 수: {result.modified_count}")

        return {
            "collection": col_name,
            "matched": result.matched_count,
            "modified": result.modified_count,
            "status": "success",
        }

    except Exception as e:
        print(f"⚠️ 마이그레이션 실패 (prefix: {prefix}): {e}")
        return {"status": "error", "message": str(e)}


async def delete_collection_documents(prefix: str, filter_query: Dict[str, Any]):
    """
    특정 컬렉션(prefix로 식별)에서 조건에 맞는 모든 문서를 삭제합니다.

    Args:
        prefix (str): 'rp-', 'pl-', 'exec-' 등 SAGEDataStore 매핑용 접두사
        filter_query (dict): 삭제 대상 조건 (MongoDB Query Filter)
    """
    try:
        col_name = saged._collection_name(prefix)
        deleted_count = await saged._backend.delete_many(col_name, filter_query)

        print(f"[{col_name}] 컬렉션 삭제 작업 완료")
        print(f"- 조건: {json.dumps(filter_query, ensure_ascii=False)}")
        print(f"- 삭제된 문서 수: {deleted_count}")

        return {
            "collection": col_name,
            "deleted_count": deleted_count,
            "status": "success",
        }

    except Exception as e:
        print(f"⚠️ 삭제 실패 (prefix: {prefix}): {e}")
        return {"status": "error", "message": str(e)}


async def get_db() -> SAGEDataStore:
    """
    FastAPI 의존성 주입을 위한 DB 인스턴스 반환 함수.
    이 함수는 각 API 요청마다 호출됩니다.
    """
    # 만약 SAGEDataStore 내부에서 비동기 연결 관리가 필요하다면
    # 여기서 연결 체크나 세션 생성을 수행할 수 있습니다.
    try:
        # 이미 생성된 saged 인스턴스를 주입
        yield saged
    finally:
        # 요청 처리가 끝난 후 수행할 정리 작업이 있다면 여기에 작성
        # 예: await saged.close_session()
        pass


# 싱글톤 인스턴스
saged = SAGEDataStore()


def _close_saged_on_exit() -> None:
    try:
        saged.close()
    except Exception:
        pass


atexit.register(_close_saged_on_exit)


async def run_system_migration():
    await migrate_collection_field("rp-", "rid", "id")
    await migrate_collection_field("pl-", "pid", "id")
    await migrate_collection_field("task-", "task_id", "id")
    await migrate_collection_field("exec-", "exec_id", "id")


if __name__ == '__main__':
    import asyncio

    # asyncio.run(run_system_migration())
    # asyncio.run(delete_collection_documents('rp-', {"status": {"$ne": "completed"}}))
    asyncio.run(migrate_collection_field('rp-', 'pid', 'plan_id'))
