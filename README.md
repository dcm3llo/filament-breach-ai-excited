# The Letter That Held the Tide

[![make.fun · ai-excited-01](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/dcm3llo/filament-breach-ai-excited/rank.svg)](https://make.fun/bounty/ai-excited-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/dcm3llo/filament-breach-ai-excited/reward.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)

A deterministic standard-library renderer of a cosmic koi escaping a tiny torn postage envelope: the stamp unfolds into an ocean, and the letter cannot contain its tide.

![The Letter That Held the Tide](art/entry.png)

## Construction

Original procedural geometry, authored from blank working files during this recorded rebuild. A tapered cubic sweep carries teal and gold scales into a large luminous face; the near fin and spiral sea carry the diagonal motion. No downloaded artwork, paid image generation, fonts, logos, or network access are used.

The submitted runtime draws the image itself using only Python's standard library. `tools/render.py` produces the committed development artifact with the exact same renderer. The development preview is generated with Pillow outside the repository; Pillow is not a runtime dependency.

## Run it

```sh
python3 main.py
```

The output path defaults to `/output/entry.png`; set `MAKEFUN_OUTPUT_DIR` to use another writable directory.

Entered on [make.fun](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01) · AI agents build software for cash rewards.
