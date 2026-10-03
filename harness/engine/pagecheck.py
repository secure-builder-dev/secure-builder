# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Render a page the way a person sees it, for a project's own tests (web track).

A string in the page proves nothing about what is drawn (antipode A-2 passed every test while
its map stayed blank), and a headless browser's --dump-dom writes nothing on Windows (antipode
A-4: zero bytes by pipe, by file and through cmd). A screenshot works everywhere. This module
takes one with whatever Chromium-family browser is installed and decodes the PNG with the
standard library, so a test can assert on pixels:

    from engine import pagecheck
    shot = pagecheck.screenshot("http://127.0.0.1:8765/")      # None when no browser is installed
    assert shot.share(lambda r, g, b: b > 100 and r < 60) > 0.2   # a fifth of the page is ocean blue

No network: the browser is pointed at the URL the test gives (the test's own loopback server).
"""
import os
import pathlib
import shutil
import struct
import subprocess
import tempfile
import zlib

CANDIDATES = ("msedge", "chrome", "chromium", "chromium-browser", "google-chrome")
WINDOWS_PATHS = (r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                 r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
                 r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                 r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                 r"%LocalAppData%\Google\Chrome\Application\chrome.exe")


def browser():
    """The path of an installed Chromium-family browser, or None."""
    for name in CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    for raw in WINDOWS_PATHS:
        p = os.path.expandvars(raw)
        if "%" not in p and os.path.isfile(p):
            return p
    return None


class Shot:
    """A decoded screenshot: width, height and rows of (r, g, b) tuples."""

    def __init__(self, width, height, rows):
        self.width, self.height, self.rows = width, height, rows

    def pixels(self):
        for row in self.rows:
            yield from row

    def share(self, predicate):
        """The fraction of pixels for which predicate(r, g, b) is true."""
        total = hits = 0
        for r, g, b in self.pixels():
            total += 1
            hits += bool(predicate(r, g, b))
        return hits / total if total else 0.0

    def colours(self, step=16):
        """How many distinct colours, quantized to `step`: a blank or single-colour page has a handful."""
        return len({(r // step, g // step, b // step) for r, g, b in self.pixels()})


def decode_png(data):
    """Decode an 8-bit RGB or RGBA, non-interlaced PNG (what Chromium writes) into a Shot."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, width = 8, [], None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or colour not in (2, 6) or interlace:
                raise ValueError(f"unsupported PNG: depth {depth}, colour type {colour}, interlace {interlace}")
            bpp = 3 if colour == 2 else 4
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + length
    if width is None:
        raise ValueError("PNG has no IHDR")
    raw = zlib.decompress(b"".join(idat))
    stride = width * bpp
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(height):
        ftype, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b, c = prev[x], (prev[x - bpp] if x >= bpp else 0)
            if ftype == 1:
                line[x] = (line[x] + a) & 255
            elif ftype == 2:
                line[x] = (line[x] + b) & 255
            elif ftype == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif ftype == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x:x + 3]) for x in range(0, stride, bpp)])
        prev = line
    return Shot(width, height, rows)


def screenshot(url, width=1280, height=800, wait_ms=10000, timeout=120):
    """Render `url` in a headless browser and return the decoded Shot, or None when no browser is
    installed (the caller skips, saying so). Raises RuntimeError when the browser runs but writes
    no image."""
    exe = browser()
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "shot.png"
        subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}",
                        f"--virtual-time-budget={wait_ms}", f"--user-data-dir={pathlib.Path(d) / 'profile'}",
                        f"--screenshot={out}", url], capture_output=True, timeout=timeout)
        if not out.is_file():
            raise RuntimeError(f"{exe} wrote no screenshot for {url}")
        return decode_png(out.read_bytes())
