import hashlib
import inspect
import json
import os
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
import tempfile
import re
import numpy as np
import pandas as pd

import cfg

# from utilx.date import to_date

# 캐시 저장소 디렉토리 설정
CACHE_BASE_DIR = cfg.dump_path / 'cache'  # Path(r'D:\\syc')
# (CACHE_BASE_DIR / 'ipp').mkdir(parents=True, exist_ok=True)
CACHE_EXT = ".syd"
DEFAULT_TTL = 1

_cleanup_lock = threading.Lock()
_cleanup_started = False

# def _make_hashable(obj):
#     """가변 객체(dict, list)를 해시 가능한 튜플 구조로 변환"""
#     if isinstance(obj, dict):
#         return tuple((k, _make_hashable(v)) for k, v in sorted(obj.items()))
#     elif isinstance(obj, list):
#         return tuple(_make_hashable(i) for i in obj)
#     return obj

# def get_func_str(func, *args, **kwargs):
#     # 함수의 시그니처를 가져와서 전달된 인자를 매개변수명에 매핑합니다.
#     sig = inspect.signature(func)
#     bound_args = sig.bind(*args, **kwargs)
#     bound_args.apply_defaults()  # 기본값이 있는 경우 포함
#
#     # 인자들을 'key=value' 형태로 변환합니다.
#     # 모든 인자를 키워드 형태로 출력하고 싶다면 bound_args.arguments를 사용합니다.
#     formatted_args = []
#     for key, value in bound_args.arguments.items():
#         formatted_args.append(f"{key}={value}")
#
#     func_str = f"{func.__name__}({', '.join(formatted_args)})"
#
#     # 요청하신 특수문자 및 공백 제거 처리
#     func_str = func_str.replace('\\', '').replace(':', '').replace("'", "").replace(' ', '')
#     if len(func_str) > 128:
#         func_str = func_str[:120] + '...'
#     return func_str

def get_func_str(func, *args, **kwargs):
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    formatted_args = []
    params = sig.parameters

    for key, value in bound_args.arguments.items():
        if params[key].kind == inspect.Parameter.VAR_KEYWORD:
            continue

        val = value
        # 1. 객체의 메모리 주소(at 0x...) 및 인스턴스 정보 정제
        # 객체가 인자로 들어올 경우 고유 식별값(클래스명 등) 위주로 추출
        val_str = str(val)
        if "at 0x" in val_str:
            # 'GeminiLLM object at 0x...' -> 'GeminiLLM' 만 추출하거나 클래스명으로 대체
            match = re.search(r'([\w\.]+)\s+object\s+at\s+0x[0-9a-fA-F]+', val_str)
            if match:
                val_str = match.group(1)
            else:
                # 일반적인 주소 형태 정규식 제거
                val_str = re.sub(r'at\s+0x[0-9a-fA-F]+', '', val_str).strip()

        formatted_args.append(f"{key}={val_str}")

    # 함수명 설정
    func_name = func.__name__
    func_str = f"{func_name}({', '.join(formatted_args)})"

    # 2. 파일명 부적합 문자 및 메모리 주소 패턴 일괄 제거
    func_str = re.sub(r'[<>:"/\\|?*\s]', '', func_str)

    # 메모리 주소 패턴(0x...)이 남아있을 경우를 대비해 한 번 더 정제
    func_str = re.sub(r'0x[0-9a-fA-F]{8,}', '', func_str)

    # 3. 특수문자 제거
    func_str = func_str.replace("'", "").replace('"', "").replace("`", "")

    # 4. 길이 제한 및 해시 처리
    if len(func_str) > 128:
        hash_suffix = hashlib.sha256(func_str.encode()).hexdigest()[:10]
        func_str = f"{func_str[:110]}_{hash_suffix}"

    return func_str

def _get_cache_path(func, args, kwargs):
    """함수와 인자를 바탕으로 함수명-해시 조합의 경로 생성"""
    # 메서드인 경우 self 인스턴스 제외 (주소값 변화 방지)
    # if args and hasattr(args[0], "__class__") and func.__name__ in dir(args[0]):
    #     relevant_args = args[1:]
    # else:
    #     relevant_args = args

    # hashable_args = _make_hashable(relevant_args)
    # hashable_kwargs = _make_hashable(kwargs)

    # 함수 식별자와 인자를 조합하여 해시 생성
    # key_source = f"{func.__module__}.{func.__qualname__}:{hashable_args}:{hashable_kwargs}"
    # cache_key = hashlib.md5(key_source.encode("utf-8")).hexdigest()

    # 2단계 디렉토리 구조 (해시 앞 2글자)
    sub_dir = CACHE_BASE_DIR / func.__name__  # cache_key[:2]
    sub_dir.mkdir(exist_ok=True)

    # make func + args as str
    func_str = get_func_str(func, *args, **kwargs)

    return sub_dir / f"{func_str}.syd"  # -{cache_key}

# def cleanup_expired_caches(cache_dir: Path, ttl: int):
#     """
#     백그라운드에서 TTL이 지난 캐시 파일을 삭제하고 누적 이력을 관리하는 함수
#     """
#     if not cache_dir.exists() or ttl <= 0:
#         return
#
#     meta_file_path = cache_dir / "cleanup.json"
#     current_date = datetime.now().date()
#
#     # 1. 기존 메타데이터 읽기 (누적 삭제 개수 및 최종 작업일 확인)
#     cumulative_deleted_count = 0
#     if meta_file_path.exists():
#         try:
#             with open(meta_file_path, "r", encoding="utf-8") as f:
#                 meta_data = json.load(f)
#                 last_cleanup_str = meta_data.get("last_cleanup_date")
#                 cumulative_deleted_count = meta_data.get("total_deleted_count", 0)
#
#                 if last_cleanup_str:
#                     last_cleanup_date = datetime.strptime(last_cleanup_str, "%Y-%m-%d").date()
#                     # 날짜 차이가 ttl보다 작으면 작업 스킵
#                     if (current_date - last_cleanup_date).days < ttl:
#                         return
#         except (json.JSONDecodeError, ValueError, KeyError):
#             pass
#
#     # 2. 파일 삭제 작업 수행
#     current_session_deleted = 0
#     try:
#         for file_path in cache_dir.glob("*.syd"):
#             if file_path.name == meta_file_path.name:
#                 continue
#
#             try:
#                 # 파일 수정일 기준 비교
#                 if (current_date - datetime.fromtimestamp(file_path.stat().st_mtime).date()).days >= ttl:
#                     file_path.unlink(missing_ok=True)
#                     current_session_deleted += 1
#             except Exception:
#                 continue
#
#         # 3. 누적 개수 업데이트 및 저장
#         history_data = {
#             "last_cleanup_date": current_date.strftime("%Y-%m-%d"),
#             "total_deleted_count": cumulative_deleted_count + current_session_deleted
#         }
#
#         with open(meta_file_path, "w", encoding="utf-8") as f:
#             json.dump(history_data, f, ensure_ascii=False, indent=4)
#
#     except Exception as e:
#         print(f"Cleanup error: {e}")

def cleanup_expired_caches():
    """
    CACHE_BASE_DIR 내의 각 하위 폴더를 순회하며 만료된 캐시를 삭제
    """
    # 기본 폴더가 없으면 작업 불필요
    if not CACHE_BASE_DIR.exists():
        return

    current_date = datetime.now().date()

    # 하위 폴더 순회
    for sub_dir in [d for d in CACHE_BASE_DIR.iterdir() if d.is_dir()]:
        meta_file_path = sub_dir / "cleanup.json"
        if not meta_file_path.exists():
            continue

        try:
            with open(meta_file_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            ttl = meta.get("ttl", DEFAULT_TTL)
            last_cleanup_str = meta.get("last_cleanup_date")
            cumulative_count = meta.get("total_deleted_count", 0)

            # 마지막 작업일이 오늘이면 중복 실행 방지를 위해 스킵
            if last_cleanup_str:
                last_cleanup_date = datetime.strptime(last_cleanup_str, "%Y-%m-%d").date()
                if (current_date - last_cleanup_date).days < ttl:
                    continue

            # 파일 삭제 작업
            session_deleted = 0
            for cache_file in sub_dir.glob(f"*{CACHE_EXT}"):
                try:
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime).date()
                    if (current_date - mtime).days >= ttl:
                        cache_file.unlink(missing_ok=True)
                        session_deleted += 1
                except Exception:
                    continue

            # 메타데이터 업데이트
            meta.update({
                "last_cleanup_date": current_date.strftime("%Y-%m-%d"),
                "total_deleted_count": cumulative_count + session_deleted
            })

            with open(meta_file_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=4)

        except Exception:
            continue

def _auto_init_cleanup():
    """
    모듈 로드 시 또는 함수 호출 시 전역적으로 1회 실행을 보장
    """
    global _cleanup_started
    if not _cleanup_started:
        with _cleanup_lock:
            if not _cleanup_started:
                threading.Thread(
                    target=cleanup_expired_caches,
                    daemon=True
                ).start()
                _cleanup_started = True

def cc(func, *args, **kwargs):
    """
    Cache Call: 개별 함수 단위 캐싱 및 메타데이터 관리
    """
    # # 1. 자동 초기화 확인 (만약 모듈 로드 시점에 실패했을 경우 대비)
    # _auto_init_cleanup()

    ttl = kwargs.pop('ttl', DEFAULT_TTL)

    # 캐시 경로 생성 (내부 유틸리티 함수 가정)
    cache_file = _get_cache_path(func, args, kwargs)
    sub_dir = cache_file.parent

    if not sub_dir.exists():
        sub_dir.mkdir(parents=True, exist_ok=True)

    # 2. 하위 폴더별 cleanup.json 관리
    meta_file = sub_dir / "cleanup.json"
    if not meta_file.exists():
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"ttl": ttl, "total_deleted_count": 0}, f, ensure_ascii=False, indent=4)

    # 3. 캐시 로드 및 TTL 체크
    if cache_file.exists():
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime).date()
            if (datetime.now().date() - mtime).days >= ttl:
                cache_file.unlink(missing_ok=True)
            else:
                return pd.read_pickle(str(cache_file))
        except Exception:
            pass

    # 4. 원본 실행 및 저장
    result = func(*args, **kwargs)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=sub_dir, delete=False, suffix=".tmp") as tf:
            temp_path = tf.name
        pd.to_pickle(result, temp_path, protocol=2)
        os.replace(temp_path, str(cache_file))
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    return result

# def cc(func, *args, **kwargs):
#     """
#     Cache Call: 함수 직접 호출 및 캐싱 (Pandas to_pickle 기반)
#     """
#     # 전역 설정 확인 및 캐시 사용 여부 결정
#     global cleanup_thread_started
#
#     ttl = kwargs.pop('ttl') if 'ttl' in kwargs else DEFAULT_TTL
#     if not getattr(cfg, "cached", True) or ttl == 0:
#         return func(*args, **kwargs)
#
#     cache_file = _get_cache_path(func, args, kwargs)
#     cache_dir = cache_file.parent
#
#     # 1. 백그라운드 정리 스레드 실행 (최초 1회 또는 주기적)
#     # if not cleanup_thread_started:
#     #     cleanup_thread = threading.Thread(
#     #         target=cleanup_expired_caches,
#     #         args=(cache_dir, ttl),
#     #         daemon=True
#     #     )
#     #     cleanup_thread.start()
#     #     cleanup_thread_started = True
#
#     # 1. 캐시 확인 및 로드
#     if cache_file.exists():
#         try:
#             if ttl > 0:
#                 # 파일의 마지막 수정 날짜 (시간 정보 제거)
#                 mtime = cache_file.stat().st_mtime
#                 last_modified_date = datetime.fromtimestamp(mtime).date()
#
#                 # 현재 날짜 (시간 정보 제거)
#                 current_date = datetime.now().date()  # to_date(cfg.end)  #
#
#                 # 1. 단순히 날짜가 달라졌는지 확인 (오후 9시 생성 -> 다음날 오후 7시 삭제)
#                 # 2. 또는 특정 일수(ttl) 이상의 날짜 차이가 나는지 확인
#                 if (current_date - last_modified_date).days >= ttl:
#                     cache_file.unlink(missing_ok=True)
#                     raise FileNotFoundError
#
#             res = pd.read_pickle(str(cache_file))
#             if isinstance(res, (pd.DataFrame, pd.Series, dict, list, np.ndarray, str, int)) or res is None:
#                 return res
#
#             raise ValueError
#
#         except Exception:
#             pass
#
#     # 2. 원본 함수 실행
#     result = func(*args, **kwargs)
#
#     # 3. 원자적 저장 (Atomic Write)
#     temp_path = None
#     try:
#         sub_dir = cache_file.parent
#         # 임시 파일 생성
#         with tempfile.NamedTemporaryFile(dir=sub_dir, delete=False, suffix=".tmp") as tf:
#             temp_path = tf.name
#
#         # protocol 4를 사용하여 32/64비트 환경 간 호환성 확보
#         pd.to_pickle(result, temp_path, protocol=2)
#
#         # 쓰기 완료 후 최종 경로로 교체 (파일 파손 방지)
#         os.replace(temp_path, str(cache_file))
#     except Exception:
#         if temp_path and os.path.exists(temp_path):
#             os.unlink(temp_path)
#
#     return result

def cache(ttl=DEFAULT_TTL):
    """데코레이터 방식 캐시"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            kwargs['ttl'] = ttl
            return cc(func, *args, **kwargs)

        return wrapper

    return decorator

# 모듈이 임포트되는 시점에 자동 실행 시도
_auto_init_cleanup()

@cache(ttl=1)
def sample(test=1):
    return test

if __name__ == '__main__':
    # print(sample(5))
    print(cc(sample, test=3))
