"""Deliver the original pre-rendered artwork without network or dependencies.
SPDX-License-Identifier: MIT
"""
import hashlib
import os
from pathlib import Path

EXPECTED_SHA256 = '593174e24351836995110f0fca6defe5fb2522e4c35a3cc539bd9994ff9dc964'


def main():
    source = Path(__file__).resolve().parent / 'art' / 'entry.png'
    data = source.read_bytes()
    # Fail before creating an output if packaging has damaged the approved art.
    # A fixed content digest is stronger than recognizing a plausible header.
    if len(data) > 1048576 or hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Packaged artwork failed integrity verification')
    destination = Path(os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'))
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'entry.png').write_bytes(data)


if __name__ == '__main__':
    main()
