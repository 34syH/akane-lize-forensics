#!/usr/bin/env python3
"""아카네 리제 이미지 포렌식 문제를 생성한다."""

from __future__ import annotations

import base64
import shutil
import struct
import subprocess
import zlib
from pathlib import Path


# 다음 문제를 만들 때는 이 세 값을 바꾸면 된다.
FLAG = "flag{L1se_Is_s00_CUt3}"
ZIP_PASSWORD = "akanelize1001"
SOURCE_FILENAME = "akane_lize.png"

ROOT = Path(__file__).resolve().parent
SOURCE_IMAGE = ROOT / "source" / SOURCE_FILENAME
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
OUTPUT_IMAGE = DIST_DIR / "akane_lize_evidence.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TEXT_CHUNKS = {b"tEXt", b"zTXt", b"iTXt"}


def make_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """길이, 종류, 데이터, CRC를 포함한 PNG 청크를 만든다."""
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def parse_png_chunks(source: bytes) -> list[tuple[bytes, bytes]]:
    """PNG를 청크 목록으로 읽고 CRC를 검사한다."""
    if not source.startswith(PNG_SIGNATURE):
        raise ValueError("원본 파일이 올바른 PNG가 아닙니다.")

    chunks: list[tuple[bytes, bytes]] = []
    offset = len(PNG_SIGNATURE)

    while offset < len(source):
        if offset + 12 > len(source):
            raise ValueError("PNG 청크가 중간에서 잘렸습니다.")

        data_length = struct.unpack(">I", source[offset : offset + 4])[0]
        chunk_end = offset + 12 + data_length
        if chunk_end > len(source):
            raise ValueError("PNG 청크 길이가 올바르지 않습니다.")

        chunk_type = source[offset + 4 : offset + 8]
        chunk_data = source[offset + 8 : offset + 8 + data_length]
        stored_crc = struct.unpack(">I", source[offset + 8 + data_length : chunk_end])[0]
        calculated_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if stored_crc != calculated_crc:
            raise ValueError(f"{chunk_type!r} 청크의 CRC가 올바르지 않습니다.")

        chunks.append((chunk_type, chunk_data))
        offset = chunk_end

        if chunk_type == b"IEND":
            return chunks

    raise ValueError("PNG에서 IEND 청크를 찾지 못했습니다.")


def paeth_predictor(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def decode_rgb_pixels(chunks: list[tuple[bytes, bytes]]) -> tuple[int, int, bytearray]:
    """8비트 RGB PNG의 필터를 복원해 RGB 바이트 배열로 변환한다."""
    ihdr = next((data for kind, data in chunks if kind == b"IHDR"), None)
    if ihdr is None or len(ihdr) != 13:
        raise ValueError("PNG IHDR 청크가 올바르지 않습니다.")

    width, height, bit_depth, color_type, compression, filtering, interlace = (
        struct.unpack(">IIBBBBB", ihdr)
    )
    if (bit_depth, color_type, compression, filtering, interlace) != (8, 2, 0, 0, 0):
        raise ValueError("8비트 RGB 비인터레이스 PNG만 지원합니다.")

    compressed = b"".join(data for kind, data in chunks if kind == b"IDAT")
    filtered = zlib.decompress(compressed)
    bytes_per_pixel = 3
    stride = width * bytes_per_pixel
    expected_length = height * (stride + 1)
    if len(filtered) != expected_length:
        raise ValueError("압축 해제된 PNG 데이터 길이가 예상과 다릅니다.")

    pixels = bytearray()
    previous = bytearray(stride)
    offset = 0

    for _ in range(height):
        filter_type = filtered[offset]
        scanline = filtered[offset + 1 : offset + 1 + stride]
        restored = bytearray(stride)

        for index, value in enumerate(scanline):
            left = restored[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            above = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = paeth_predictor(left, above, upper_left)
            else:
                raise ValueError(f"지원하지 않는 PNG 필터입니다: {filter_type}")

            restored[index] = (value + predictor) & 0xFF

        pixels.extend(restored)
        previous = restored
        offset += stride + 1

    return width, height, pixels


def encode_rgb_png(
    chunks: list[tuple[bytes, bytes]], width: int, height: int, pixels: bytearray
) -> bytes:
    """RGB 배열을 필터 0으로 재압축하고 텍스트 메타데이터 없이 PNG를 만든다."""
    stride = width * 3
    scanlines = bytearray()
    for row in range(height):
        start = row * stride
        scanlines.append(0)
        scanlines.extend(pixels[start : start + stride])

    new_idat = zlib.compress(bytes(scanlines), level=9)
    result = bytearray(PNG_SIGNATURE)
    idat_written = False

    for chunk_type, chunk_data in chunks:
        if chunk_type in TEXT_CHUNKS:
            continue
        if chunk_type == b"IDAT":
            if not idat_written:
                result.extend(make_png_chunk(b"IDAT", new_idat))
                idat_written = True
            continue
        result.extend(make_png_chunk(chunk_type, chunk_data))

    if not idat_written:
        raise ValueError("PNG에서 IDAT 청크를 찾지 못했습니다.")
    return bytes(result)


def embed_lsb_message(source: bytes, message: str) -> bytes:
    """RGB 채널 LSB에 ASCII 메시지와 NULL 종료 문자를 숨긴다."""
    chunks = parse_png_chunks(source)
    width, height, pixels = decode_rgb_pixels(chunks)
    payload = message.encode("ascii") + b"\x00"
    required_channels = len(payload) * 8
    if required_channels > len(pixels):
        raise ValueError("이미지의 LSB 용량이 메시지보다 작습니다.")

    channel_index = 0
    for byte in payload:
        # RGB 채널 LSB에 기록하고 zsteg의 b1,rgb,lsb,xy 순서로 읽히게 한다.
        for bit_index in range(7, -1, -1):
            bit = (byte >> bit_index) & 1
            pixels[channel_index] = (pixels[channel_index] & 0xFE) | bit
            channel_index += 1

    return encode_rgb_png(chunks, width, height, pixels)


def main() -> None:
    if shutil.which("zip") is None:
        raise RuntimeError("시스템에 zip 명령이 필요합니다.")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 플래그를 담은 암호화 ZIP을 만든다.
    flag_path = BUILD_DIR / "flag.txt"
    archive_path = BUILD_DIR / "secret.zip"
    flag_path.write_text(FLAG + "\n", encoding="utf-8")
    archive_path.unlink(missing_ok=True)
    subprocess.run(
        [
            "zip",
            "-j",
            "-q",
            "-9",
            "-X",
            "-P",
            ZIP_PASSWORD,
            str(archive_path),
            str(flag_path),
        ],
        check=True,
    )

    # ZIP 비밀번호를 Base64로 인코딩해 RGB 채널의 LSB에 숨긴다.
    encoded_password = base64.b64encode(ZIP_PASSWORD.encode("ascii")).decode("ascii")
    png_data = embed_lsb_message(SOURCE_IMAGE.read_bytes(), encoded_password)

    # PNG의 정상적인 끝 뒤에 ZIP 데이터를 이어 붙인다.
    OUTPUT_IMAGE.write_bytes(png_data + archive_path.read_bytes())

    print(f"문제 파일: {OUTPUT_IMAGE}")
    print(f"LSB 단서: {encoded_password}")


if __name__ == "__main__":
    main()
