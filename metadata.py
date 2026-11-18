"""Lossless XMP (title/description) embedding for JPEG, PNG and WebP files.

Image data is never re-encoded: the XMP packet is spliced into the container.
"""
import html
import re
import struct
import zlib

XMP_JPEG_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


def htmlToText(t):
    """Turn padlet post html into plain text, keeping emojis and line breaks."""
    t = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</div>", "\n", t or "")
    t = re.sub(r"<!--.*?-->|<[^>]*>", "", t, flags=re.S)
    t = html.unescape(t)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n")]
    return "\n".join(l for l in lines if l)


def _xmpPacket(title, description):
    def alt(tag, value):
        if not value:
            return ""
        return ('<dc:%s><rdf:Alt><rdf:li xml:lang="x-default">%s</rdf:li></rdf:Alt></dc:%s>'
                % (tag, html.escape(value, quote=False), tag))

    return ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
            + alt("title", title) + alt("description", description) +
            '</rdf:Description></rdf:RDF></x:xmpmeta>'
            '<?xpacket end="w"?>').encode("utf-8")


def _jpeg(data, xmp):
    if data[:2] != b"\xff\xd8":
        return None
    payload = XMP_JPEG_HEADER + xmp
    if len(payload) + 2 > 0xFFFF:
        return None
    segment = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload

    out, pos, inserted = [data[:2]], 2, False
    while pos + 4 <= len(data) and data[pos] == 0xFF:
        marker = data[pos + 1]
        if marker == 0xDA:  # start of scan, rest is image data
            break
        length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        seg = data[pos:pos + 2 + length]
        if not inserted and marker not in (0xE0, 0xE1):
            out.append(segment)
            inserted = True
        if not (marker == 0xE1 and seg[4:4 + len(XMP_JPEG_HEADER)] == XMP_JPEG_HEADER):
            out.append(seg)  # drop any previous XMP
        pos += 2 + length
    if not inserted:
        out.append(segment)
    out.append(data[pos:])
    return b"".join(out)


def _png(data, xmp):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    body = b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + xmp
    chunk = struct.pack(">I", len(body)) + b"iTXt" + body + struct.pack(">I", zlib.crc32(b"iTXt" + body))

    out, pos, inserted = [data[:8]], 8, False
    while pos + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        raw = data[pos:pos + 12 + length]
        if ctype == b"IDAT" and not inserted:
            out.append(chunk)
            inserted = True
        if not (ctype == b"iTXt" and raw[8:26] == b"XML:com.adobe.xmp\x00"):
            out.append(raw)
        pos += 12 + length
    return b"".join(out) if inserted else None


def _webp(data, xmp):
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunks, pos = [], 12
    while pos + 8 <= len(data):
        fourcc, size = struct.unpack("<4sI", data[pos:pos + 8])
        chunks.append([fourcc, data[pos + 8:pos + 8 + size]])
        pos += 8 + size + (size & 1)
    if not chunks:
        return None

    if chunks[0][0] != b"VP8X":
        fourcc, bits = chunks[0]
        alpha = 0
        if fourcc == b"VP8 " and bits[3:6] == b"\x9d\x01\x2a":
            w = struct.unpack("<H", bits[6:8])[0] & 0x3FFF
            h = struct.unpack("<H", bits[8:10])[0] & 0x3FFF
        elif fourcc == b"VP8L" and bits[:1] == b"\x2f":
            v = struct.unpack("<I", bits[1:5])[0]
            w, h, alpha = (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1, (v >> 28) & 1
        else:
            return None
        flags = 0x10 if alpha else 0
        vp8x = bytes([flags, 0, 0, 0]) + struct.pack("<I", w - 1)[:3] + struct.pack("<I", h - 1)[:3]
        chunks.insert(0, [b"VP8X", vp8x])

    vp8x = bytearray(chunks[0][1])
    vp8x[0] |= 0x04  # XMP present
    chunks[0][1] = bytes(vp8x)
    chunks = [c for c in chunks if c[0] != b"XMP "] + [[b"XMP ", xmp]]

    body = b"WEBP" + b"".join(
        c[0] + struct.pack("<I", len(c[1])) + c[1] + (b"\x00" if len(c[1]) & 1 else b"")
        for c in chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def writeMetadata(path, title, description):
    """Embed title/description as XMP. Returns False if the format is unsupported."""
    with open(path, "rb") as f:
        data = f.read()
    xmp = _xmpPacket(title, description)
    for writer in (_jpeg, _png, _webp):
        result = writer(data, xmp)
        if result is not None:
            with open(path, "wb") as f:
                f.write(result)
            return True
    return False
