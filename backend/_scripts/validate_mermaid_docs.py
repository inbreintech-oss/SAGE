"""Extract and validate mermaid blocks from docs/docs.md."""
import re
import subprocess
import tempfile
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "docs" / "docs.md").read_text(encoding="utf-8")
blocks = re.findall(r"```mermaid\n(.*?)```", text, re.S)
print(f"Found {len(blocks)} blocks\n")

for i, b in enumerate(blocks, 1):
    with tempfile.TemporaryDirectory() as td:
        inp = Path(td) / "diagram.mmd"
        out = Path(td) / "diagram.svg"
        inp.write_text(b, encoding="utf-8")
        r = subprocess.run(
            [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli@11.4.0",
                "-i",
                str(inp),
                "-o",
                str(out),
                "-b",
                "transparent",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        ok = r.returncode == 0 and out.exists()
        status = "OK" if ok else "FAIL"
        print(f"Block {i}: {status}")
        if not ok:
            err = (r.stderr or r.stdout or "").strip()
            if err:
                print(err[:800])
            print("--- snippet ---")
            print("\n".join(b.splitlines()[:8]))
            print("---")
