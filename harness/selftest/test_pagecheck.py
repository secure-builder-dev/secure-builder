# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The render probe decodes what Chromium writes, so a project's test can assert on drawn pixels
(antipode A-4: --dump-dom is empty on Windows; only a screenshot shows what is drawn)."""
import struct
import unittest
import zlib

from engine import pagecheck


def png(rows, filters, alpha=False):
    """A PNG of `rows` (lists of (r, g, b)) with the given per-row filter types, encoded the way a
    writer would: each row stored as the difference the filter predicts."""
    bpp = 4 if alpha else 3
    raw, prev = bytearray(), bytearray(len(rows[0]) * bpp)
    for row, f in zip(rows, filters):
        line = bytearray()
        for r, g, b in row:
            line += bytes((r, g, b, 255) if alpha else (r, g, b))
        enc = bytearray()
        for x in range(len(line)):
            a = line[x - bpp] if x >= bpp else 0
            up, c = prev[x], (prev[x - bpp] if x >= bpp else 0)
            if f == 0:
                pred = 0
            elif f == 1:
                pred = a
            elif f == 2:
                pred = up
            elif f == 3:
                pred = (a + up) // 2
            else:
                p = a + up - c
                pa, pb, pc = abs(p - a), abs(p - up), abs(p - c)
                pred = a if pa <= pb and pa <= pc else up if pb <= pc else c
            enc.append((line[x] - pred) & 255)
        raw += bytes([f]) + enc
        prev = line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", len(rows[0]), len(rows), 8, 6 if alpha else 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")


ROWS = [[(10, 30, 120), (11, 31, 121), (250, 250, 250)],
        [(12, 40, 130), (200, 10, 10), (5, 5, 5)],
        [(13, 50, 140), (14, 60, 150), (15, 70, 160)],
        [(0, 0, 0), (255, 255, 255), (128, 128, 128)],
        [(1, 2, 3), (4, 5, 6), (7, 8, 9)]]


class Decode(unittest.TestCase):
    def test_every_filter_type_decodes_to_the_original_pixels(self):
        for alpha in (False, True):
            shot = pagecheck.decode_png(png(ROWS, [0, 1, 2, 3, 4], alpha=alpha))
            self.assertEqual((shot.width, shot.height), (3, 5))
            self.assertEqual(shot.rows, ROWS, f"alpha={alpha}")

    def test_share_and_colours_measure_what_is_drawn(self):
        shot = pagecheck.decode_png(png(ROWS, [0] * 5))
        self.assertAlmostEqual(shot.share(lambda r, g, b: b > 100 and r < 60), 6 / 15)
        self.assertGreater(shot.colours(), 5)
        blank = pagecheck.decode_png(png([[(9, 9, 9)] * 3] * 5, [0] * 5))
        self.assertEqual(blank.colours(), 1)

    def test_a_non_png_is_refused(self):
        with self.assertRaises(ValueError):
            pagecheck.decode_png(b"GIF89a")


if __name__ == "__main__":
    unittest.main()
