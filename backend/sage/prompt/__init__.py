"""Prompt composition and dataset context loading."""

from sage.prompt.core import (
    BASE_DIR,
    compose,
    dotprompts_dir,
    find_model_prompt,
    replace_args,
    resolve_pattern,
)
from sage.prompt.dataset import get_data_profile, load_schema, read_schema_file

__all__ = [
    "BASE_DIR",
    "dotprompts_dir",
    "find_model_prompt",
    "resolve_pattern",
    "replace_args",
    "compose",
    "load_schema",
    "read_schema_file",
    "get_data_profile",
]
