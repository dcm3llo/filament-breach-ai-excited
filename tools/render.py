#!/usr/bin/env python3
"""Development renderer: writes the same bytes as the submitted runtime."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import main  # noqa: E402

output = Path(os.environ.get("RENDER_OUTPUT", ROOT / "art" / "entry.png"))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(main.render())
print(f"rendered {output} ({output.stat().st_size} bytes)")
