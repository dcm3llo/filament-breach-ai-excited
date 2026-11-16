#!/usr/bin/env python3
"""Deterministic, standard-library-only renderer for the cosmic-letter koi poster."""
from __future__ import annotations

from collections.abc import Sequence
import math
import os
import struct
import zlib
from pathlib import Path

WIDTH = 768
HEIGHT = 768
MAX_BYTES = 1048576


def clamp(value: float) -> int:
    return max(0, min(255, int(value + 0.5)))


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))


def encode_png(rgb: bytes, width: int = WIDTH, height: int = HEIGHT) -> bytes:
    rows = b"".join(b"\x00" + rgb[y * width * 3:(y + 1) * width * 3]
                   for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" +
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            png_chunk(b"IDAT", zlib.compress(rows, 9)) + png_chunk(b"IEND", b""))


def render() -> bytes:
    pixels = bytearray(WIDTH * HEIGHT * 3)

    def put(x: int, y: int, color: tuple[float, float, float], alpha: float = 1.0) -> None:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT and alpha > 0:
            i = (y * WIDTH + x) * 3
            a = max(0.0, min(1.0, alpha))
            pixels[i] = clamp(pixels[i] * (1 - a) + color[0] * a)
            pixels[i + 1] = clamp(pixels[i + 1] * (1 - a) + color[1] * a)
            pixels[i + 2] = clamp(pixels[i + 2] * (1 - a) + color[2] * a)

    def glow(cx: float, cy: float, radius: float, color: tuple[float, float, float], strength: float) -> None:
        left, right = max(0, int(cx - radius)), min(WIDTH, int(cx + radius + 1))
        top, bottom = max(0, int(cy - radius)), min(HEIGHT, int(cy + radius + 1))
        for y in range(top, bottom):
            for x in range(left, right):
                d = math.hypot(x - cx, y - cy) / radius
                if d < 1:
                    put(x, y, color, (1 - d) ** 2 * strength)

    def line(points: Sequence[tuple[float, float]], color: tuple[float, float, float], width: float, alpha: float = 1.0) -> None:
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            length = max(1, int(math.hypot(x1 - x0, y1 - y0) * 2))
            for step in range(length + 1):
                t = step / length
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                r = max(1, int(width / 2))
                for oy in range(-r, r + 1):
                    for ox in range(-r, r + 1):
                        if ox * ox + oy * oy <= r * r:
                            put(int(x + ox), int(y + oy), color, alpha)

    def polygon(points: Sequence[tuple[float, float]], color: tuple[float, float, float], alpha: float = 1.0) -> None:
        points = list(points)
        ys = range(max(0, int(min(y for _, y in points))), min(HEIGHT, int(max(y for _, y in points) + 1)))
        for y in ys:
            hits = []
            for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
                if (y0 <= y < y1) or (y1 <= y < y0):
                    hits.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            hits.sort()
            for a, b in zip(hits[::2], hits[1::2]):
                for x in range(max(0, int(a)), min(WIDTH, int(b) + 1)):
                    put(x, y, color, alpha)

    def ellipse(cx: float, cy: float, rx: float, ry: float, color: tuple[float, float, float], alpha: float = 1.0) -> None:
        for y in range(max(0, int(cy - ry)), min(HEIGHT, int(cy + ry + 1))):
            dy = (y - cy) / ry
            half = rx * math.sqrt(max(0, 1 - dy * dy))
            for x in range(max(0, int(cx - half)), min(WIDTH, int(cx + half + 1))):
                put(x, y, color, alpha)

    # Deep blue negative space with a faint radial aurora.
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx, dy = (x - 420) / 560, (y - 365) / 560
            aura = max(0, 1 - math.hypot(dx, dy))
            grain = ((x * 17 + y * 31) % 13) / 13
            put(x, y, (3 + 4 * aura, 9 + 18 * aura, 27 + 37 * aura + grain), 1)
    glow(545, 246, 300, (0, 74, 105), 0.22)
    glow(277, 575, 220, (10, 31, 100), 0.28)

    # Postage stamp becomes a spiral ocean: warm paper shards and a cyan vortex.
    envelope = [(116, 573), (246, 522), (337, 578), (226, 659)]
    polygon(envelope, (244, 213, 159), 1)
    polygon([(116, 573), (226, 659), (205, 700), (90, 615)], (166, 93, 69), 1)
    polygon([(246, 522), (337, 578), (315, 618), (226, 659)], (255, 231, 179), 1)
    line([(116, 573), (226, 659), (337, 578)], (255, 249, 215), 3, 0.75)
    # Torn mouth and a recognisable perforated postage stamp at the source.
    polygon([(116, 573), (141, 559), (157, 570), (178, 548), (192, 558),
             (216, 535), (231, 548), (246, 522), (268, 540), (223, 599)], (10, 29, 48))
    polygon([(250, 550), (283, 554), (293, 582), (259, 577)], (255, 247, 205))
    polygon([(257, 556), (278, 559), (284, 575), (263, 572)], (25, 149, 177))
    for j in range(6):
        ellipse(251+j*6, 550+j*.7, 1.6, 1.6, (10, 29, 48))
        ellipse(260+j*6, 578+j*.7, 1.6, 1.6, (10, 29, 48))
    line([(274, 564), (300, 546), (325, 517)], (230, 245, 190), 3, .8)
    # Stamp folded into a luminous whirlpool.
    for ring in range(16):
        pts = []
        for j in range(45):
            t = j / 44 * math.pi * 2.5 + ring * 0.17
            radius = 20 + ring * 7 + j * 1.0
            pts.append((223 + math.cos(t) * radius * 1.4, 578 + math.sin(t) * radius * 0.46))
        line(pts, (28 + ring * 5, 213 + ring * 2, 214 + ring * 2), 2, 0.75)
    glow(222, 580, 105, (24, 221, 210), 0.24)

    # Koi trajectory: a sweeping body from the envelope to a large head near the viewer.
    spine = [(202, 591), (288, 539), (355, 448), (430, 337), (527, 226), (620, 166)]
    # Tail and long fins behind the body.
    polygon([(232, 573), (147, 482), (180, 596), (112, 646), (244, 622)], (19, 154, 174), 0.9)
    polygon([(279, 522), (205, 423), (321, 483), (367, 388), (349, 530)], (13, 111, 151), 0.78)
    polygon([(401, 373), (447, 221), (480, 341), (541, 242), (505, 405)], (22, 192, 191), 0.68)
    line([(232, 573), (147, 482), (180, 596), (112, 646)], (91, 238, 222), 4, 0.75)
    line([(280, 521), (205, 423), (321, 483), (367, 388)], (79, 219, 213), 3, 0.62)

    # A continuous cubic sweep avoids the segmented anatomy of the first draft.
    def frame(t: float) -> tuple[float, float, float, float, float]:
        u = 1 - t
        x = u**3 * 212 + 3*u*u*t*440 + 3*u*t*t*314 + t**3*593
        y = u**3 * 589 + 3*u*u*t*534 + 3*u*t*t*235 + t**3*194
        dx = 3*u*u*(440-212) + 6*u*t*(314-440) + 3*t*t*(593-314)
        dy = 3*u*u*(534-589) + 6*u*t*(235-534) + 3*t*t*(194-235)
        length = math.hypot(dx, dy)
        return x, y, -dy / length, dx / length, 13 + 72*t**0.85

    left, right = [], []
    for j in range(121):
        x, y, nx, ny, width = frame(j / 120)
        left.append((x + nx*width, y + ny*width))
        right.append((x - nx*width, y - ny*width))
    polygon(left + right[::-1], (19, 122, 146), 1)
    # Broad longitudinal bands establish volume without a disconnected necklace.
    for band in range(24):
        a, b = band / 24, (band + 1) / 24
        strip = []
        for j in range(101):
            x, y, nx, ny, width = frame(j / 100)
            strip.append((x + nx*width*(2*a-1), y + ny*width*(2*a-1)))
        for j in range(100, -1, -1):
            x, y, nx, ny, width = frame(j / 100)
            strip.append((x + nx*width*(2*b-1), y + ny*width*(2*b-1)))
        light = math.sin((band + .5) / 24 * math.pi)
        color = (clamp(18 + 232*light**2), clamp(91 + 114*light), clamp(119 + 26*light))
        polygon(strip, color, 1)
    line(right, (255, 235, 165), 4, 0.92)
    line(left, (74, 246, 228), 3, 0.85)
    # Each scale is attached to the local tangent rather than screen-aligned.
    for row in range(22):
        t = .12 + row*.037
        x, y, nx, ny, width = frame(t)
        tx, ty = ny, -nx
        for col in range(7):
            across = (col - 3 + .35*(row % 2)) / 3.8
            sx, sy = x + nx*width*across, y + ny*width*across
            size = 3 + 8*t
            points = [(sx + nx*size*math.cos(k*math.pi/8) + tx*size*.7*math.sin(k*math.pi/8),
                       sy + ny*size*math.cos(k*math.pi/8) + ty*size*.7*math.sin(k*math.pi/8))
                      for k in range(9)]
            color = (255, 228, 139) if (row+col)%5 == 0 else (32, 205, 197)
            line(points, color, 2, .8)
    # Foreshortened near fin reaches toward the lower-right foreground.
    fin = [(453, 302), (659, 356), (698, 493), (597, 429), (507, 408), (446, 358)]
    polygon(fin, (12, 105, 140), .92)
    line(fin + [fin[0]], (87, 238, 220), 3, .8)
    for j in range(14):
        t = j / 13
        line([(455+36*t, 319+43*t), (565+94*t, 359+69*t), (698-101*t, 493-64*t)],
             (107, 224, 199), 2, .7)
    # Dorsal fin rays keep its translucent structure intentional.
    for j in range(10):
        t = j/9
        line([(406+88*t, 369-30*t), (447+59*t, 221+91*t)], (133, 242, 207), 2, .42)

    # Huge head, bright mask, whiskers, and eyes aimed at the viewer.
    glow(635, 137, 165, (255, 172, 45), 0.26)
    ellipse(625, 151, 125, 96, (246, 177, 55), 1)
    ellipse(615, 132, 94, 72, (255, 243, 197), 0.9)
    polygon([(559, 155), (500, 100), (571, 116), (604, 153)], (20, 175, 181), 0.9)
    polygon([(675, 164), (758, 105), (720, 188), (695, 218)], (15, 145, 164), 0.9)
    ellipse(596, 126, 18, 22, (4, 22, 48), 1)
    ellipse(596, 121, 7, 9, (255, 255, 230), 1)
    ellipse(678, 145, 20, 24, (4, 22, 48), 1)
    ellipse(682, 138, 7, 9, (255, 255, 230), 1)
    line([(598, 185), (632, 194), (668, 184)], (116, 45, 45), 7, 0.9)
    line([(606, 206), (648, 214), (689, 201)], (255, 245, 196), 4, 0.8)
    line([(585, 175), (532, 165), (493, 184)], (226, 200, 104), 3, 0.65)
    line([(696, 183), (745, 208), (767, 239)], (226, 200, 104), 3, 0.65)

    # Starlight spray and small glints keep the diagonal readable at thumbnail size.
    for k in range(42):
        angle = 2.9 + (k % 11) * 0.14
        radius = 85 + (k * 37) % 230
        cx = 573 + math.cos(angle) * radius
        cy = 213 + math.sin(angle) * radius * 0.68
        glow(cx, cy, 7 + (k % 4), (255, 223, 120), 0.45)
        ellipse(cx, cy, 1.8 + k % 3, 1.8 + k % 2, (255, 248, 197), 0.95)
    for x, y in [(84, 102), (151, 178), (702, 356), (92, 354), (370, 105), (704, 610)]:
        line([(x - 10, y), (x + 10, y)], (107, 221, 231), 2, 0.8)
        line([(x, y - 10), (x, y + 10)], (255, 231, 151), 2, 0.8)

    return encode_png(bytes(pixels))


def main() -> None:
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    data = render()
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > MAX_BYTES:
        raise RuntimeError("renderer produced an invalid or oversized PNG")
    (output_dir / "entry.png").write_bytes(data)


if __name__ == "__main__":
    main()
