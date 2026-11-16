"""Independent structural and execution checks; Python standard library only.
SPDX-License-Identifier: MIT
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path(os.environ.get('MAKEFUN_TEST_EVIDENCE', tempfile.gettempdir()))


def verify_png(data):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('PNG signature')
    pos, chunks, compressed = 8, [], bytearray()
    width = height = None
    while pos < len(data):
        if len(data) - pos < 12:
            raise ValueError('Truncated chunk')
        length = struct.unpack_from('>I', data, pos)[0]
        end = pos + 12 + length
        if end > len(data):
            raise ValueError('Truncated payload')
        kind = data[pos+4:pos+8]
        payload = data[pos+8:pos+8+length]
        crc = struct.unpack_from('>I', data, pos+8+length)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            raise ValueError('CRC mismatch')
        if not chunks and kind != b'IHDR':
            raise ValueError('IHDR must be first')
        if kind == b'IHDR':
            if chunks or length != 13:
                raise ValueError('Invalid or duplicate IHDR')
            width,height,depth,color,method,filtering,interlace = struct.unpack('>IIBBBBB',payload)
            if not (1 <= width <= 1024 and 1 <= height <= 1024):
                raise ValueError('Dimensions')
            if (depth,color,method,filtering,interlace) != (8,2,0,0,0):
                raise ValueError('Expected noninterlaced RGB8 artwork')
        elif kind == b'IDAT':
            if b'IDAT' in chunks and chunks[-1] != b'IDAT':
                raise ValueError('Non-contiguous IDAT')
            compressed.extend(payload)
        elif kind == b'IEND':
            if length != 0 or end != len(data) or not compressed:
                raise ValueError('Invalid end')
        elif kind[:1].isupper():
            raise ValueError('Unsupported critical chunk')
        chunks.append(kind)
        pos = end
    if not chunks or chunks[-1] != b'IEND' or width is None or height is None:
        raise ValueError('Missing image header or end')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed) + decoder.flush()
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('Incomplete or trailing zlib stream')
    stride = 1 + width * 3
    if len(raw) != stride * height:
        raise ValueError('Wrong decompressed scanline length')
    if any(raw[i*stride] > 4 for i in range(height)):
        raise ValueError('Invalid scanline filter')
    if len(data) > 1048576:
        raise ValueError('Image size')
    return {'width':width,'height':height,'bytes':len(data),
            'scanline_bytes':len(raw),'sha256':hashlib.sha256(data).hexdigest(),
            'chunks':[c.decode('ascii') for c in chunks]}


def chunk(kind, payload):
    return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.data = (ROOT/'art'/'entry.png').read_bytes()

    def test_artifact_complete(self):
        result = verify_png(self.data)
        self.assertEqual((result['width'],result['height']),(1024,1024))

    def test_adversarial_truncations(self):
        for amount in (1,4,12,40,len(self.data)//2,len(self.data)-8):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                verify_png(self.data[:-amount])

    def test_crc_corruption(self):
        damaged=bytearray(self.data)
        damaged[29] ^= 1
        with self.assertRaisesRegex(ValueError,'CRC'):
            verify_png(bytes(damaged))

    def test_missing_end_and_trailing_bytes(self):
        for data in (self.data[:-12],self.data+b'junk'):
            with self.assertRaises(ValueError):
                verify_png(data)

    def test_scanline_mismatch_with_valid_crc(self):
        header=struct.pack('>IIBBBBB',10,10,8,2,0,0,0)
        fake=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',zlib.compress(b'\0'*10))+chunk(b'IEND',b'')
        with self.assertRaisesRegex(ValueError,'scanline length'):
            verify_png(fake)

    def test_actual_runtime_twice(self):
        EVIDENCE.mkdir(parents=True,exist_ok=True)
        before = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
        runs=[]
        outputs=[]
        for i in range(2):
            with tempfile.TemporaryDirectory(prefix=f'runtime-{i}-',dir=EVIDENCE) as folder:
                output=Path(folder)/'nested'/'output'
                env=os.environ.copy()
                env['MAKEFUN_OUTPUT_DIR']=str(output)
                env['PYTHONDONTWRITEBYTECODE']='1'
                start=time.perf_counter()
                process=subprocess.run([sys.executable,'-I','-B',str(ROOT/'main.py')],cwd=folder,env=env,capture_output=True,timeout=60)
                elapsed=time.perf_counter()-start
                self.assertEqual(process.returncode,0,process.stderr.decode())
                self.assertEqual(process.stdout,b'')
                self.assertEqual(process.stderr,b'')
                self.assertEqual(sorted(p.name for p in output.iterdir()),['entry.png'])
                data=(output/'entry.png').read_bytes()
                self.assertEqual(data,self.data)
                outputs.append(data)
                (EVIDENCE/f'runtime-run-{i+1}.png').write_bytes(data)
                runs.append({'run':i+1,'elapsed_seconds':elapsed,'output_override':True,**verify_png(data)})
        self.assertEqual(outputs[0],outputs[1])
        after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
        self.assertEqual(before,after,'Runtime modified repository')
        (EVIDENCE/'runtime-report.json').write_text(json.dumps({'runs':runs,'repo_unchanged':True,'python':sys.version},indent=2))

    def test_runtime_rejects_damaged_asset_before_output(self):
        EVIDENCE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='damaged-package-',dir=EVIDENCE) as folder:
            package=Path(folder)
            (package/'art').mkdir()
            (package/'main.py').write_bytes((ROOT/'main.py').read_bytes())
            damaged=bytearray(self.data)
            damaged[len(damaged)//2] ^= 1
            (package/'art'/'entry.png').write_bytes(damaged)
            output=package/'out'
            env=os.environ.copy()
            env['MAKEFUN_OUTPUT_DIR']=str(output)
            process=subprocess.run([sys.executable,'-I','-B',str(package/'main.py')],env=env,capture_output=True,timeout=60)
            self.assertNotEqual(process.returncode,0)
            self.assertIn(b'failed integrity',process.stderr)
            self.assertFalse(output.exists())

    def test_runtime_readonly_and_no_network_audit(self):
        # Enforce the sandbox properties through Python's audit interface.
        # This is a host-side proxy, not a claim of official container grading.
        EVIDENCE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='audit-output-',dir=EVIDENCE) as folder:
            output=Path(folder)/'output'
            wrapper='''import sys, os, runpy
from pathlib import Path
out=Path(sys.argv[2]).resolve()
def audit(event,args):
    if event.startswith('socket.'):
        raise RuntimeError('Network denied')
    if event == 'open':
        target,mode,flags=args
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and not Path(target).resolve().is_relative_to(out):
            raise RuntimeError('Write outside output denied')
    if event == 'os.mkdir' and not Path(args[0]).resolve().is_relative_to(out):
        raise RuntimeError('mkdir outside output denied')
sys.addaudithook(audit)
runpy.run_path(sys.argv[1],run_name='__main__')
'''
            env=os.environ.copy()
            env['MAKEFUN_OUTPUT_DIR']=str(output)
            process=subprocess.run([sys.executable,'-I','-B','-c',wrapper,str(ROOT/'main.py'),str(output)],env=env,capture_output=True,timeout=60)
            self.assertEqual(process.returncode,0,process.stderr.decode())
            self.assertEqual((output/'entry.png').read_bytes(),self.data)

    def test_entrypoint_stdlib_and_default(self):
        import ast
        tree=ast.parse((ROOT/'main.py').read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.extend(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:
                imports.append(node.module.split('.')[0])
        self.assertTrue(set(imports) <= {'hashlib','os','pathlib'})
        self.assertIn("'/output'",(ROOT/'main.py').read_text())


if __name__=='__main__':
    unittest.main(verbosity=2)
