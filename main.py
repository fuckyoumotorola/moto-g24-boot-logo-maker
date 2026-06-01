#!/usr/bin/env python3
import argparse
import struct
import sys
import zlib
from pathlib import Path
from PIL import Image, ImageOps

MTK_HEADER_SIZE = 512
U32 = "<I"

DEFAULT_WIDTH = 720
DEFAULT_HEIGHT = 1612


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from(U32, data, off)[0]


def p32(value: int) -> bytes:
    return struct.pack(U32, value)


def read_logo(path: Path):
    data = path.read_bytes()

    if len(data) < MTK_HEADER_SIZE + 8:
        raise ValueError("The file is too small to be a valid MTK logo.bin.")

    header = data[:MTK_HEADER_SIZE]

    if data[8:12].upper() != b"LOGO":
        print("[WARN] LOGO signature was not found at offset 0x08. I will try to parse it anyway.")

    count = u32(data, MTK_HEADER_SIZE)
    block_size = u32(data, MTK_HEADER_SIZE + 4)

    if count <= 0 or count > 128:
        raise ValueError(f"Unexpected image count: {count}")

    offsets_base = MTK_HEADER_SIZE + 8
    offsets = [
        u32(data, offsets_base + i * 4)
        for i in range(count)
    ]

    if offsets[0] != 8 + count * 4:
        print(f"[WARN] Unexpected initial offset: {offsets[0]}")

    parts = []

    for i in range(count):
        start = MTK_HEADER_SIZE + offsets[i]

        if i + 1 < count:
            end = MTK_HEADER_SIZE + offsets[i + 1]
        else:
            end = MTK_HEADER_SIZE + block_size

        if start < 0 or end > len(data) or end <= start:
            raise ValueError(f"Invalid offsets in slot {i}: start={start}, end={end}")

        compressed = data[start:end]

        try:
            raw = zlib.decompress(compressed)
        except zlib.error:
            raw = None
            print(f"[WARN] Slot {i}: could not decompress it with zlib.")

        parts.append({
            "index": i,
            "compressed": compressed,
            "raw": raw,
        })

    return {
        "original_size": len(data),
        "header": header,
        "count": count,
        "parts": parts,
    }


def infer_mode(raw_len: int, width: int, height: int) -> str:
    pixels = width * height

    if raw_len == pixels * 3:
        return "rgb888"

    if raw_len == pixels * 4:
        return "bgra8888"

    if raw_len == pixels * 2:
        return "rgb565le"

    raise ValueError(
        "Could not infer the slot format.\n"
        f"raw_len={raw_len}, expected RGB888={pixels*3}, BGRA8888={pixels*4}, RGB565={pixels*2}\n"
        "Try using the correct --width/--height values or --mode rgb888|bgra8888|rgb565le."
    )


def prepare_image(image_path: Path, width: int, height: int, resize_mode: str) -> Image.Image:
    img = Image.open(image_path).convert("RGBA")

    if resize_mode == "stretch":
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        return img

    if resize_mode == "cover":
        return ImageOps.fit(img, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    # contain
    bg = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    fitted = ImageOps.contain(img, (width, height), method=Image.Resampling.LANCZOS)
    x = (width - fitted.width) // 2
    y = (height - fitted.height) // 2
    bg.paste(fitted, (x, y), fitted)
    return bg


def image_to_raw(img: Image.Image, mode: str) -> bytes:
    if mode == "rgb888":
        return img.convert("RGB").tobytes()

    if mode == "bgr888":
        rgb = img.convert("RGB").tobytes()
        out = bytearray(len(rgb))
        for i in range(0, len(rgb), 3):
            r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
            out[i:i + 3] = bytes((b, g, r))
        return bytes(out)

    if mode == "bgra8888":
        rgba = img.convert("RGBA").tobytes()
        out = bytearray(len(rgba))
        for i in range(0, len(rgba), 4):
            r, g, b, a = rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]
            out[i:i + 4] = bytes((b, g, r, a))
        return bytes(out)

    if mode == "rgba8888":
        return img.convert("RGBA").tobytes()

    if mode == "rgb565le":
        rgb = img.convert("RGB").tobytes()
        out = bytearray()

        for i in range(0, len(rgb), 3):
            r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]

            value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            out += struct.pack("<H", value)

        return bytes(out)

    raise ValueError(f"Unsupported mode: {mode}")


def repack_logo(parsed, new_compressed_parts):
    count = parsed["count"]
    header = parsed["header"]

    offsets = []
    current_offset = 8 + count * 4

    for part in new_compressed_parts:
        offsets.append(current_offset)
        current_offset += len(part)

    block_size = current_offset

    out = bytearray()
    out += header
    out += p32(count)
    out += p32(block_size)

    for off in offsets:
        out += p32(off)

    for part in new_compressed_parts:
        out += part

    return bytes(out)


def main():
    parser = argparse.ArgumentParser(
        description="Creates a custom MTK/Motorola logo.bin using stock_logo.bin as a template."
    )

    parser.add_argument("image", help="Input PNG/JPG/WebP image.")
    parser.add_argument("-t", "--template", default="stock_logo.bin", help="Original logo.bin. Default: stock_logo.bin")
    parser.add_argument("-o", "--output", default="logo.bin", help="Output file. Default: logo.bin")
    parser.add_argument("--slot", default="0", help="Slot to replace. Default: 0. Use 'all' for all fullscreen slots.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Width. Default: 720")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Height. Default: 1612")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "rgb888", "bgr888", "bgra8888", "rgba8888", "rgb565le"],
        help="Raw logo format. Default: auto"
    )
    parser.add_argument(
        "--resize",
        default="contain",
        choices=["contain", "cover", "stretch"],
        help="How to fit the image. contain = no cropping, cover = cropped, stretch = distorted. Default: contain"
    )
    parser.add_argument(
        "--allow-bigger",
        action="store_true",
        help="Allows generating a logo.bin bigger than the original one. Not recommended."
    )

    args = parser.parse_args()

    image_path = Path(args.image)
    template_path = Path(args.template)
    output_path = Path(args.output)

    if not image_path.exists():
        print(f"[ERROR] Image does not exist: {image_path}")
        sys.exit(1)

    if not template_path.exists():
        print(f"[ERROR] {template_path} does not exist")
        print("Place your original logo file in the same folder and name it stock_logo.bin.")
        sys.exit(1)

    parsed = read_logo(template_path)

    print(f"[INFO] Images inside logo: {parsed['count']}")
    print(f"[INFO] Original size: {parsed['original_size']} bytes")

    parts = [p["compressed"] for p in parsed["parts"]]

    slots_to_replace = []

    if args.slot == "all":
        for p in parsed["parts"]:
            if p["raw"] is None:
                continue

            try:
                mode = args.mode
                if mode == "auto":
                    mode = infer_mode(len(p["raw"]), args.width, args.height)

                expected_len = len(image_to_raw(
                    prepare_image(image_path, args.width, args.height, args.resize),
                    mode
                ))

                if len(p["raw"]) == expected_len:
                    slots_to_replace.append(p["index"])
            except Exception:
                pass
    else:
        slots_to_replace = [int(args.slot)]

    if not slots_to_replace:
        print("[ERROR] There are no slots to replace.")
        sys.exit(1)

    img = prepare_image(image_path, args.width, args.height, args.resize)

    for slot in slots_to_replace:
        if slot < 0 or slot >= parsed["count"]:
            print(f"[ERROR] Invalid slot: {slot}")
            sys.exit(1)

        original_raw = parsed["parts"][slot]["raw"]

        mode = args.mode
        if mode == "auto":
            if original_raw is None:
                print(f"[ERROR] Cannot infer mode because slot {slot} could not be decompressed.")
                sys.exit(1)

            mode = infer_mode(len(original_raw), args.width, args.height)

        raw = image_to_raw(img, mode)
        compressed = zlib.compress(raw, level=9)

        parts[slot] = compressed

        print(f"[INFO] Replaced slot: {slot}")
        print(f"[INFO] Used mode: {mode}")
        print(f"[INFO] New raw size: {len(raw)} bytes")
        print(f"[INFO] New compressed size: {len(compressed)} bytes")

    new_logo = repack_logo(parsed, parts)

    original_size = parsed["original_size"]

    if len(new_logo) > original_size and not args.allow_bigger:
        print("[ERROR] The new logo.bin is bigger than the original one.")
        print(f"Original: {original_size} bytes")
        print(f"New:      {len(new_logo)} bytes")
        print("I will not generate it like this for safety. Try using a simpler/darker image or use --allow-bigger at your own risk.")
        sys.exit(1)

    if len(new_logo) < original_size:
        new_logo += b"\x00" * (original_size - len(new_logo))

    output_path.write_bytes(new_logo)

    print(f"[OK] Generated: {output_path}")
    print(f"[OK] Final size: {output_path.stat().st_size} bytes")


if __name__ == "__main__":
    main()