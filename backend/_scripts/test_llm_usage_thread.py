"""ContextVar + copy_context — LLM thread 경로 및 동시 요청 격리."""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars

from sage.llm.usage import (
    begin_report_generation,
    current_usage,
    record_llm_usage,
    reset_report_generation,
)


def _record_in_copied_context(
    ctx: contextvars.Context,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """generate_async 와 동일 — copy_context().run() 안에서 record."""

    def _inner() -> None:
        record_llm_usage(
            "gemini-2.0-flash",
            input_tokens,
            output_tokens,
            provider="gemini",
        )

    ctx.run(_inner)


async def _one_report(thread_in: int, main_in: int):
    begin_report_generation()
    try:
        ctx = contextvars.copy_context()
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(
                pool,
                _record_in_copied_context,
                ctx,
                thread_in,
                50,
            )
        record_llm_usage("gemini-2.0-flash", main_in, 10, provider="gemini")
        stats = current_usage()
        assert stats is not None
        return stats
    finally:
        reset_report_generation()


async def main() -> None:
    begin_report_generation()
    ctx = contextvars.copy_context()
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, _record_in_copied_context, ctx, 100, 50)
    stats = current_usage()
    assert stats is not None and stats.calls == 1 and stats.input_tokens == 100
    reset_report_generation()
    print("OK: copy_context thread records usage")

    a, b = await asyncio.gather(_one_report(100, 200), _one_report(1000, 2000))
    assert a.input_tokens == 300, a.to_dict()
    assert b.input_tokens == 3000, b.to_dict()
    print("OK: concurrent report usage isolated")


if __name__ == "__main__":
    asyncio.run(main())
