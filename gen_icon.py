#!/usr/bin/env python3
"""Generate Stone dashboard PNG icon — no dependencies required."""
import struct, zlib, pathlib

def solid_png(size, r, g, b):
    scanline = bytes([0]) + bytes([r, g, b]) * size
    raw = scanline * size
    compressed = zlib.compress(raw, 9)
    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

here = pathlib.Path(__file__).parent
(here / 'icon-180.png').write_bytes(solid_png(180, 12, 40, 24))   # #0C2818
(here / 'icon-512.png').write_bytes(solid_png(512, 12, 40, 24))
print('icon-180.png and icon-512.png written')
