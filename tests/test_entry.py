import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG = b"\x89PNG\r\n\x1a\n"


def inspect_png(data):
    assert len(data) <= 1048576, 'oversize PNG'
    assert data.startswith(PNG)
    pos = 8
    chunks = []
    compressed = bytearray()
    while pos < len(data):
        assert pos + 12 <= len(data), "truncated chunk header"
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + size
        assert end <= len(data), "truncated chunk payload"
        payload = data[pos + 8:pos + 8 + size]
        crc = struct.unpack(">I", data[pos + 8 + size:end])[0]
        assert zlib.crc32(kind + payload) & 0xffffffff == crc, "bad CRC"
        chunks.append((kind, payload))
        if kind == b"IDAT":
            compressed.extend(payload)
        pos = end
        if kind == b"IEND":
            break
    assert pos == len(data), "trailing bytes"
    assert [kind for kind, _ in chunks] == [b'IHDR', b'IDAT', b'IEND'], 'chunk order/completeness'
    assert chunks[-1][1] == b'', 'IEND must be empty'
    width, height, depth, color, comp, filt, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    assert (width, height, depth, color, comp, filt, interlace) == (768, 768, 8, 2, 0, 0, 0)
    raw = zlib.decompress(bytes(compressed))
    assert len(raw) == height * (1 + width * 3)
    assert all(raw[y * (1 + width * 3)] == 0 for y in range(height))
    # Actually exercise EOF on the complete stream and reject appended garbage.
    dec = zlib.decompressobj()
    dec.decompress(bytes(compressed))
    assert dec.eof and dec.unused_data == b""
    return width, height, raw, chunks


class EntryTests(unittest.TestCase):
    def run_once(self, directory):
        env = os.environ.copy()
        env["MAKEFUN_OUTPUT_DIR"] = str(directory)
        subprocess.run([sys.executable, '-B', str(ROOT / "main.py")], cwd=directory, env=env, check=True, timeout=60)
        return (directory / "entry.png").read_bytes()

    def test_two_fresh_runs_are_identical_and_complete(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = self.run_once(Path(a))
            second = self.run_once(Path(b))
            self.assertEqual(first, second)
            self.assertLessEqual(len(first), 1048576)
            inspect_png(first)
            self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())

    def test_corruption_and_truncation_are_rejected(self):
        with tempfile.TemporaryDirectory() as a:
            data = self.run_once(Path(a))
        with self.assertRaises(AssertionError):
            inspect_png(data[:-9])
        broken = bytearray(data)
        broken[29] ^= 1
        with self.assertRaises(AssertionError):
            inspect_png(bytes(broken))
        _, _, raw, chunks = inspect_png(data)
        compressed = b''.join(payload for kind, payload in chunks if kind == b'IDAT')
        decoder = zlib.decompressobj()
        decoder.decompress(compressed[:-4])
        self.assertFalse(decoder.eof)
        def pack(kind, payload):
            return struct.pack('>I', len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
        for stream in (compressed[:-4], compressed+b'junk', zlib.compress(raw[:-1])):
            bad = PNG + pack(b'IHDR', chunks[0][1]) + pack(b'IDAT', stream) + pack(b'IEND', b'')
            with self.assertRaises((AssertionError, zlib.error)):
                inspect_png(bad)
        for bad in (data[1:], data[:40], data[:-1], data[:-12], data+b'junk'):
            with self.assertRaises((AssertionError, zlib.error)):
                inspect_png(bad)

    def test_stdlib_import_audit(self):
        import ast
        tree = ast.parse((ROOT/'main.py').read_text(encoding='utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module.split('.')[0])
        self.assertTrue(names <= sys.stdlib_module_names)
        self.assertFalse(names & {'socket', 'urllib', 'http', 'subprocess'})

    def test_no_network_readonly_repository_proxy(self):
        runner = r'''
import os, pathlib, runpy, sys
root = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(os.environ['MAKEFUN_OUTPUT_DIR']).resolve()
def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
        raise PermissionError('forbidden network/process')
    if event == 'open':
        path, mode, flags = args
        writing = (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and not pathlib.Path(path).resolve().is_relative_to(out):
            raise PermissionError('write outside output')
    if event in ('os.mkdir','os.remove','os.rmdir','os.rename'):
        if not pathlib.Path(args[0]).resolve().is_relative_to(out):
            raise PermissionError('mutation outside output')
sys.addaudithook(audit)
runpy.run_path(str(root/'main.py'),run_name='__main__')
'''
        with tempfile.TemporaryDirectory() as directory:
            env={**os.environ,'MAKEFUN_OUTPUT_DIR':directory,'PYTHONDONTWRITEBYTECODE':'1'}
            result=subprocess.run([sys.executable,'-B','-c',runner,str(ROOT)],cwd=directory,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((Path(directory)/'entry.png').read_bytes(),(ROOT/'art/entry.png').read_bytes())
            for probe in ("import socket; socket.socket()", "open(root/'forbidden.txt','w')"):
                script=runner.replace("runpy.run_path(str(root/'main.py'),run_name='__main__')",probe)
                result=subprocess.run([sys.executable,'-B','-c',script,str(ROOT)],env=env,capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('PermissionError',result.stderr)


if __name__ == "__main__":
    unittest.main()
