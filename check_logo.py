import struct
import zlib
from pathlib import Path

MTK_HEADER_SIZE = 512


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def main():
    path = Path("logo.bin")
    data = path.read_bytes()

    print(f"[INFO] logo.bin size: {len(data)} bytes")

    if len(data) > 0x880000:
        print("[ERROR] The file exceeds 0x880000 bytes")
        return

    count = u32(data, MTK_HEADER_SIZE)
    block_size = u32(data, MTK_HEADER_SIZE + 4)

    print(f"[INFO] Image count: {count}")
    print(f"[INFO] Block size: {block_size}")

    if count <= 0 or count > 128:
        print("[ERROR] Invalid image count")
        return

    if block_size <= 0 or block_size > len(data):
        print("[ERROR] Invalid block size")
        return

    offsets_base = MTK_HEADER_SIZE + 8
    offsets = [u32(data, offsets_base + i * 4) for i in range(count)]

    if offsets != sorted(offsets):
        print("[ERROR] Offsets are not sorted")
        return

    ok = 0
    fail = 0

    for i in range(count):
        start = MTK_HEADER_SIZE + offsets[i]
        end = MTK_HEADER_SIZE + (offsets[i + 1] if i + 1 < count else block_size)

        if start < MTK_HEADER_SIZE or end > len(data) or end <= start:
            print(f"[ERROR] Slot {i}: invalid offsets start={start}, end={end}")
            fail += 1
            continue

        compressed = data[start:end]

        try:
            raw = zlib.decompress(compressed)
            print(f"[OK] Slot {i}: compressed={len(compressed)} raw={len(raw)}")
            ok += 1
        except zlib.error as e:
            print(f"[ERROR] Slot {i}: invalid zlib data: {e}")
            fail += 1

    print("")
    print(f"[RESULT] OK={ok} FAIL={fail}")

    if fail == 0:
        print("[OK] logo.bin appears to be structurally valid.")
    else:
        print("[ERROR] Some slots are corrupted. Do not flash it.")


if __name__ == "__main__":
    main()