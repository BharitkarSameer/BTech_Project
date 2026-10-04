"""Write simple solid-color PNGs for the PWA (no Pillow required)."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public"


def _png(path: Path, size: int, rgb=(45, 138, 80)) -> None:
    raw = b"".join(b"\x00" + bytes(rgb) * size for _ in range(size))
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    _png(OUT / "icon-192.png", 192)
    _png(OUT / "icon-512.png", 512)
    print("wrote icons")


if __name__ == "__main__":
    main()
