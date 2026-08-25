# metadata.json 구조

`targets[]` 는 기존 구조 유지. 하단에 루트 `tools`·`fields` 추가.

```json
{
  "sources": [
    {"id": "src-...", "type": "file", "path": "...", "adapter": "FileStockAdapter"},
    {"id": "src-...", "type": "tool", "tool_path": "kis/stock", "adapter": "KisStockAdapter"}
  ],
  "targets": [
    {
      "model": "PangeaSchema",
      "path": "stock_master.parquet",
      "keys": ["ticker"],
      "fields": ["ticker", "company_name", "sector", "price", "..."]
    },
    {
      "model": "StockPriceSeries",
      "path": "stock_prices.parquet",
      "keys": ["ticker", "date"],
      "fields": ["ticker", "date", "open_price", "close_price", "volume"]
    }
  ],
  "tools": {
    "kis/stock": {"fields": ["close_price", "volume", "price", "per"]}
  },
  "fields": {
    "_default_ttl": 1,
    "debt_rate": {"ttl": 10}
  },
  "payload_field_aliases": {
    "code": "ticker",
    "name": "company_name",
    "close": "close_price"
  }
}
```

- `targets[].fields`: parquet 컬럼 list
- `tools`: tool_path → 해당 도구가 채우는 컬럼
- `fields`: TTL 일수 (`_default_ttl` + 필드별 override)
- `payload_field_aliases` *(선택)*: MCP/API raw key → `targets[].fields` canonical name. **도메인·어댑터별** — 플랫폼 기본값 없음
