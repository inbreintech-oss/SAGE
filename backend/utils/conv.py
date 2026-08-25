import json
import re

import numpy as np
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from typing import Any

class ExtendedEncoder(json.JSONEncoder):
    """NumPy와 같은 특수 타입을 자동으로 처리하는 인코더"""

    def default(self, obj):
        if isinstance(obj, (np.ndarray, np.generic)):
            return obj.tolist()
        if hasattr(obj, 'isoformat'):  # 날짜/시간 데이터 대응
            return obj.isoformat()
        return super().default(obj)

def json_dumps(data, pretty=False):
    """
    들여쓰기(pretty)와 특수 타입 처리를 한 번에 수행하는 함수
    """
    kwargs = {
        "cls": ExtendedEncoder,
        "ensure_ascii": False,
        "separators": (',', ':') if not pretty else None
    }
    if pretty:
        kwargs["indent"] = 2

    return json.dumps(data, **kwargs)

def convert_list_to_html(data_list):
    """
    데이터셋 목록(JSON 형식의 리스트)을 받아 HTML 테이블 문자열로 변환합니다.

    :param data_list: [{'name': '...', 'description': '...'}, ...] 형태의 리스트
    :return: HTML <table> 문자열
    """
    if not data_list:
        return "<p>표시할 데이터셋 정보가 없습니다.</p>"

    # 1. HTML 테이블 시작 및 헤더 정의
    html_output = """
    <table border="1" style="width:100%; border-collapse: collapse;">
        <thead>
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 10px; text-align: left; width: 20%;">데이터셋 이름</th>
                <th style="padding: 10px; text-align: left;">설명</th>
            </tr>
        </thead>
        <tbody>
    """

    # 2. 데이터 행 추가
    for item in data_list:
        name = item.get("name", "N/A")
        description = item.get("description", "설명 없음")

        # HTML 행 (<tr>) 및 데이터 셀 (<td>) 구성
        html_output += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{name}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{description}</td>
            </tr>
        """

    # 3. HTML 테이블 닫기
    html_output += """
        </tbody>
    </table>
    """

    return html_output

def convert_info_to_html(data_info: dict) -> str:
    """
    JSON 데이터셋 메타데이터를 파싱하여 HTML 테이블로 변환합니다.
    Optional[type]과 같은 복합 타입을 처리할 수 있도록 수정되었습니다.
    """
    description_html = data_info['meta'].get('description', '설명 없음').replace('\\n', '<br>')

    props = data_info['schema'].get('properties', [])
    table_rows = []

    for prop_name, prop_info in props.items():
        # 1. 타입(dtype) 추출 로직 개선
        raw_type = prop_info.get('type')

        if isinstance(raw_type, list):
            # ['number', 'null'] 형태인 경우 null을 제외한 실제 타입 추출
            actual_types = [t for t in raw_type if t != 'null']
            dtype = actual_types[0] if actual_types else 'unknown'
            is_optional = 'null' in raw_type
        elif 'anyOf' in prop_info:
            # anyOf 구조인 경우 처리
            any_of = prop_info['anyOf']
            types = [item.get('type') for item in any_of if item.get('type') != 'null']
            dtype = types[0] if types else 'unknown'
            is_optional = any(item.get('type') == 'null' for item in any_of)
        else:
            dtype = raw_type if raw_type else 'unknown'
            is_optional = False

        description = prop_info.get('description', '설명 없음')

        # 2. 데이터 타입별 스타일 및 레이블 결정
        dtype_class = 'text-gray-500 bg-gray-100'
        if dtype == 'string':
            dtype_class = 'text-blue-700 bg-blue-50'
        elif dtype in ['integer', 'number']:
            dtype_class = 'text-green-700 bg-green-50'

        # Optional 표시 추가
        optional_badge = '<span class="ml-1 text-[10px] text-gray-500 font-bold border border-gray-200 px-1 rounded">OPT</span>' if is_optional else ''

        row = f"""
        <tr class="hover:bg-gray-50 transition-colors">
            <td class="px-3 py-3 whitespace-nowrap text-sm font-mono text-indigo-700 font-semibold">{prop_name}</td>
            <td class="px-3 py-3 whitespace-nowrap text-sm">
                <span class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-bold uppercase {dtype_class}">
                    {dtype}
                </span>
                {optional_badge}
            </td>
            <td class="px-6 py-3 text-sm text-gray-600 leading-snug">{description}</td>
        </tr>
        """
        table_rows.append(row)

    table_rows_html = "\n".join(table_rows)
    column_count = len(props)

    # 전체 HTML 레이아웃 (이전과 동일하되 디자인 소폭 개선)
    html_template = f"""
    <div class="p-4 md:p-8 max-w-7xl mx-auto font-sans">
        <div class="bg-white p-6 rounded-xl shadow-md mb-8 border-l-8 border-indigo-600">
            <h1 class="text-2xl font-black text-gray-900 mb-2">Dataset Documentation</h1>
            <p class="text-gray-600 leading-relaxed">{description_html}</p>
        </div>

        <div class="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
            <div class="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-800">컬럼 상세 목록</h2>
                <span class="bg-indigo-600 text-white text-xs px-2.5 py-1 rounded-full font-bold">Total {column_count}</span>
            </div>

            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-100">
                        <tr>
                            <th class="px-3 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/4">Name</th>
                            <th class="px-3 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/5">Type</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Description</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {table_rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    return html_template

import json
import re

def _format_value(key, value):
    """
    키에 상관없이 값의 타입만을 기준으로 포맷합니다. (숫자 콤마 포맷팅만 적용)
    """
    if isinstance(value, float):
        return f'{value:,.2f}'

    return str(value)

def _clean_column_description(description: str) -> str:
    """
    주어진 설명을 정제합니다.
    1. 첫 번째 공백 문자(' ') 앞에서 문자열을 자릅니다.
    2. 결과 문자열에서 특수 문자(영문, 한글, 숫자, 공백, 쉼표, 마침표를 제외한 문자)를 제거합니다.

    Args:
        description: 정제할 문자열 (예: '시장구분 (KOSPI/KOSDAQ/KONEX 중 1)').

    Returns:
        정제된 문자열 (예: '시장구분').
    """
    if not description:
        return description

    first_space_index = description.find(' ')
    if first_space_index != -1:
        cleaned_str = description[:first_space_index]
    else:
        cleaned_str = description

    # 결과 문자열에서 특수 문자 제거 (한글, 영문, 숫자만 남기고 나머지 제거)
    cleaned_str = re.sub(r'[^가-힣a-zA-Z0-9]', '', cleaned_str)

    return cleaned_str

def _get_column_description(key, data_info):
    """
    data_info에서 주어진 키에 대한 한국어 설명을 찾습니다.
    (stock, drug 등 모든 데이터셋을 순회하며 찾습니다.)
    """
    for prop, info in data_info['schema']['properties'].items():
        # for column in info.get('properties', []):
        if prop == key:
            return _clean_column_description(info['description'])
    # 일치하는 설명이 없으면 원래 키를 반환
    return key

def _convert_generic_table_to_html(data, data_info):
    """
    일반적인 딕셔너리 리스트 데이터를 HTML 테이블로 변환합니다.
    data_info를 사용하여 컬럼 이름을 한국어 설명으로 대체합니다.

    Args:
        data (list): 테이블 데이터 (딕셔너리 리스트).
        data_info (dict): 컬럼 메타데이터 (DATA_INFO).

    Returns:
        str: HTML 테이블 문자열.
    """
    if not data:
        return "<p>No table data available.</p>"

    # 첫 번째 행을 기준으로 키(컬럼 순서)를 정의
    keys = list(data[0].keys())

    html = '<table>'

    # 1. 헤더 (th): data_info를 사용하여 설명 대체
    html += '<thead><tr>'
    for key in keys:
        header_text = _get_column_description(key, data_info)
        html += f'<th>{header_text}</th>'
    html += '</tr></thead>'

    # 2. 바디 (td)
    html += '<tbody>'
    for row in data:
        html += '<tr>'
        for key in keys:
            value = row.get(key, '')
            formatted_value = _format_value(key, value)
            # 모든 셀은 중앙 정렬을 기본으로 가정하고 <td>를 사용
            html += f'<td>{formatted_value}</td>'
        html += '</tr>'
    html += '</tbody>'
    html += '</table>'

    return html

def _convert_markdown_to_html_with_placeholders(markdown_text, placeholder_map, metadata={}):
    """
    마크다운 텍스트를 HTML로 변환하고 플레이스홀더 및 메타데이터를 대체합니다.
    """

    # 메타데이터 플레이스홀더 ({key}) 처리
    for key, value in metadata.items():
        markdown_text = markdown_text.replace(f'{{{key}}}', value)

    lines = markdown_text.split('\n')
    html_lines = []

    for line in lines:
        stripped_line = line.strip()

        # 1. 플레이스홀더 대체 (최우선)
        match = re.match(r'\[\[(.*?)\]\]', stripped_line)
        if match:
            placeholder_key = match.group(1).split(':')[0]

            if placeholder_key in placeholder_map:
                html_lines.append(placeholder_map[placeholder_key])
            else:
                html_lines.append(f'<p style="color: red;">Placeholder not found: {stripped_line}</p>')
            continue

        # 2. Markdown 요소 변환
        if stripped_line.startswith('# '):
            html_lines.append(f'<h1>{stripped_line[2:].strip()}</h1>')
        elif stripped_line.startswith('## '):
            html_lines.append(f'<h2>{stripped_line[3:].strip()}</h2>')
        elif stripped_line.startswith('>'):
            content = stripped_line[1:].strip().replace('**', '<b>').replace('</b>', '</b>')
            html_lines.append(f'<div class="markdown-quote"><p>{content}</p></div>')
        elif stripped_line:
            if stripped_line.startswith('- '):
                content = stripped_line[2:].strip().replace('**', '<b>').replace('</b>', '</b>')
                html_lines.append(f'<p style="margin-left: 20px;">• {content}</p>')
            else:
                content = stripped_line.replace('**', '<b>').replace('</b>', '</b>')
                html_lines.append(f'<p>{content}</p>')
        else:
            html_lines.append('')

    return '\n'.join(html_lines)

def convert_report_json_to_html(report_data, data_info):
    """
    JSON 보고서 데이터를 HTML로 변환합니다. (크기 문제 해결 CSS 적용)

    Args:
        report_data (list): 다양한 tool_name을 가진 결과가 포함된 JSON 데이터 목록.
        data_info (dict): 컬럼 메타데이터 (DATA_INFO).

    Returns:
        str: 변환된 HTML 문자열.
    """

    data_map = {}
    report_text = ""

    # 1. 데이터 분류
    for item in report_data:
        tool_name = item.get('tool_name')
        result = item.get('result', {})

        if tool_name:
            if 'data' in result and not 'text' in result:
                # 테이블 데이터 (data만 포함)
                table_data = result.get('data', [])
                if table_data:
                    # **주의:** _convert_generic_table_to_html 함수는
                    # <div class="table-wrapper"><table>...</table></div> 형태로 HTML을 반환해야 합니다.
                    html_table = _convert_generic_table_to_html(table_data, data_info)
                    data_map[tool_name] = html_table

            elif 'chart' in result and not 'text' in result:
                # 차트 플레이스홀더 (chart만 포함)
                data_map[tool_name] = f''

            elif 'text' in result and not report_text:
                # 메인 리포트 텍스트
                report_text = result.get('text', '')

    if not report_text:
        return "<div>Error: Main report text ('text' field in the result) not found in the input data.</div>"

    # 2. Markdown 텍스트를 HTML로 변환하고 플레이스홀더 처리
    html_content = _convert_markdown_to_html_with_placeholders(report_text, data_map,
                                                               metadata={'start_date': '2025년 11월 25일'})

    # 3. HTML 템플릿에 최종 내용 삽입 (CSS 포함)
    final_html = f"""
<!--
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>데이터 기반 LLM 자동 보고서</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        /* 💡 1. 가로 오버플로우 방지: 최대 너비를 800px 대신 뷰포트의 90%로 설정 */
        .report-container {{ max-width: 90%; margin: auto; padding: 20px; border: 1px solid #ccc; border-radius: 8px; }}
        h1 {{ border-bottom: 2px solid #0056b3; padding-bottom: 5px; color: #0056b3; }}
        h2 {{ color: #333; }}
        /* 💡 2. 테이블 레이아웃 제어: width: 100% 유지, table-layout: fixed 추가 */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            /* ❌ max-height는 테이블에 직접 적용해도 작동하지 않으므로 제거 */
            table-layout: fixed;
        }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        /* 💡 3. 셀 내용 오버플로우 방지: 셀 내용이 길면 강제 줄바꿈 */
        td {{ word-break: break-all; }}
        .markdown-quote {{ border-left: 5px solid #ffcc00; padding: 10px; background-color: #fff9e6; margin: 15px 0; }}

        /* 💡 4. 세로 스크롤을 위한 래퍼 정의 (긴 테이블을 이 div로 감싸야 작동) */
        .table-wrapper {{
            max-height: 300px; /* 원하는 최대 높이 설정 */
            overflow-y: auto; /* 세로 스크롤바 생성 */
            margin: 15px 0;
            border: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
-->
    <div class="report-container">
        {html_content}
    </div>
<!--
</body>
</html>
-->
"""
    return final_html

def sanitize_value(val: Any) -> Any:
    """
    유입된 임의의 값을 JSON 직렬화 및 물리 장부 적재가 가능한
    순수 파이썬 primitive 타입(str, int, float, None)으로 무결하게 변환합니다.
    """
    # 1. 판다스/넘파이 결측치(NaN, NaT, None) 검출 및 None 통합
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass

    # 2. 넘파이 수치형 객체(numpy.int64, float64, bool_ 등) 분해
    if isinstance(val, np.generic):
        return sanitize_value(val.item())

    # 3. 파이썬 표준 datetime.datetime 또는 datetime.date 객체 정제
    if isinstance(val, (datetime, date)):
        return val.isoformat()

    # 4. 판다스/넘파이 시간 타입
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    if isinstance(val, np.datetime64):
        return pd.Timestamp(val).isoformat()

    if isinstance(val, Decimal):
        return float(val)

    if isinstance(val, (bytes, bytearray)):
        return val.decode("utf-8", errors="replace")

    return val

def sanitize_tree(obj: Any) -> Any:
    """dict/list 트리 — queue_update·context JSON 저장 전 공통 정규화."""
    if isinstance(obj, dict):
        return {k: sanitize_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_tree(v) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize_tree(v) for v in obj]
    return sanitize_value(obj)
