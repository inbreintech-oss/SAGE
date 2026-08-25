import time
import os
import msgpack
import pandas as pd
from datetime import datetime, date

class TimestampData:
    def __init__(self, file_path):
        self.file_path = file_path
        self.default_ttl = 1

        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            return {"ttls": {}, "ts_data": []}
        try:
            with open(self.file_path, 'rb') as f:
                return msgpack.unpack(f, raw=False)
        except Exception:
            return {"ttls": {}, "ts_data": []}

    def _save(self):
        with open(self.file_path, 'wb') as f:
            msgpack.pack(self.data, f, use_bin_type=True)

    def _is_expired(self, last_ts, ttl):
        last_date = datetime.fromtimestamp(last_ts).date()
        today = date.today()
        return (today - last_date).days >= ttl

    def set_ttl(self, field, days):
        self.data['ttls'][field] = days
        self._save()

    def _normalize_key(self, key):
        """비교·저장용 key — list/tuple/date/numpy 를 hashable 형태로 통일."""
        if isinstance(key, (list, tuple)):
            return tuple(self._normalize_key(k) for k in key)
        if isinstance(key, (date, datetime)):
            return key.isoformat()
        if hasattr(key, 'item'):
            return key.item()
        return key

    def plan_updates(self, req_keys, req_fields):
        ret_keys_norm = [self._normalize_key(k) for k in req_keys]
        mask = pd.DataFrame(False, index=ret_keys_norm, columns=req_fields)

        for box in self.data.get('ts_data', []):
            # msgpack 복원 시 tuple → list 이므로 box 쪽도 normalize
            box_keys = {self._normalize_key(k) for k in box.get('keys', [])}

            for field in box['fields']:
                if field not in req_fields:
                    continue
                ttl = self.data['ttls'].get(field, self.default_ttl)

                if not self._is_expired(box['timestamp'], ttl):
                    is_multiple_key_type = True if isinstance(list(box_keys)[0], tuple) else False
                    box_keys_slimed = {box[0] for box in box_keys} if is_multiple_key_type else box_keys
                    common_keys = [k for k in ret_keys_norm if k in box_keys_slimed]
                    if common_keys:
                        mask.loc[common_keys, field] = True

        raw_plan = []
        for field in req_fields:
            missing_keys = mask.index[~mask[field]].tolist()
            if missing_keys:
                raw_plan.append({"keys": missing_keys, "field": field})

        if not raw_plan:
            return []

        df_plan = pd.DataFrame(raw_plan)
        df_plan['keys_tuple'] = df_plan['keys'].apply(
            lambda keys: tuple(self._normalize_key(k) for k in keys)
        )

        grouped = df_plan.groupby('keys_tuple').agg({
            'keys': 'first',
            'field': lambda x: list(x),
        }).reset_index(drop=True)

        return [{"keys": row['keys'], "fields": row['field']} for _, row in grouped.iterrows()]

    def _is_covered(self, box_keys, box_fields, new_keys, new_fields):
        return new_keys.issuperset(box_keys) and new_fields.issuperset(box_fields)

    def update(self, keys, fields, ts=None):
        normalized_keys = [self._normalize_key(k) for k in keys]
        target_ts = ts if ts is not None else time.time()

        new_keys_set = set(normalized_keys)
        new_fields_set = set(fields)

        new_ts_data = []
        for box in self.data.get('ts_data', []):
            box_keys_set = {self._normalize_key(k) for k in box.get('keys', [])}
            box_fields_set = set(box['fields'])
            if not self._is_covered(box_keys_set, box_fields_set, new_keys_set, new_fields_set):
                new_ts_data.append(box)

        new_ts_data.append({"keys": normalized_keys, "fields": fields, "timestamp": target_ts})
        self.data['ts_data'] = new_ts_data
        self._save()

    def update_from_parquet(self, file_path, keys_cols):
        df = pd.read_parquet(file_path)
        if isinstance(keys_cols, list):
            if len(keys_cols) > 1:
                keys = list(df[keys_cols].itertuples(index=False, name=None))
            else:
                keys = df[keys_cols[0]].tolist()
        else:
            keys = df[keys_cols].tolist()

        normalized_keys = [self._normalize_key(k) for k in keys]
        fields = df.columns.difference(keys_cols if isinstance(keys_cols, list) else [keys_cols]).tolist()
        self.update(normalized_keys, fields)
