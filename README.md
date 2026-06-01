# MTK / Motorola Custom Boot Logo Generator

A Python tool to create a custom `logo.bin` for MTK-based Motorola devices by using an original stock `logo.bin` as a template.

This script replaces one or more image slots inside a stock MTK `logo.bin` file with your own PNG, JPG, or WebP image, then repacks the file so it can be flashed back to the device.

> **Warning**
>
> Flashing firmware partitions always involves risk. A broken or invalid `logo.bin` may cause boot logo issues or other unexpected behavior. Always keep a backup of your original `logo.bin` before flashing anything.

---

## Features

- Uses an original `stock_logo.bin` as a safe template.
- Supports PNG, JPG, and WebP input images.
- Can replace a single logo slot or all compatible fullscreen slots.
- Supports multiple raw logo formats:
  - `rgb888`
  - `bgr888`
  - `bgra8888`
  - `rgba8888`
  - `rgb565le`
- Can automatically detect the slot format when possible.
- Keeps the final file size equal to the original by padding with zero bytes.
- Prevents generating a larger file than the original unless explicitly allowed.

---

## Requirements

- Python 3.8 or newer
- Pillow

Install the required dependency:

```bash
pip install pillow
```

---

## Files Needed

Before running the script, place these files in the same folder:

```text
main.py
stock_logo.bin
your_image.png
```

Where:

- `main.py` is the Python script.
- `stock_logo.bin` is your original logo partition dump.
- `your_image.png` is the image you want to use as the boot logo.

You can also use `.jpg`, `.jpeg`, or `.webp` images.

---

## Basic Usage

```bash
python main.py image.png
```

This will:

1. Read `stock_logo.bin` from the current folder.
2. Replace slot `0` by default.
3. Generate a new file called `logo.bin`.

---

## Flashing the Generated Logo

After generating `logo.bin`, you can flash it with fastboot:

```bash
fastboot flash logo logo.bin
```

Then reboot:

```bash
fastboot reboot
```

> **Important**
>
> Make sure your device actually uses a `logo` partition and that your original `stock_logo.bin` came from the same device model and firmware family.

---

## Full Command Syntax

```bash
python main.py <image> [options]
```

Example:

```bash
python main.py boot.png -t stock_logo.bin -o logo.bin --slot 0 --width 720 --height 1612 --mode auto --resize contain
```

---

## Parameters

### Positional Arguments

| Argument | Description |
| --- | --- |
| `image` | Input image file. Supported formats: PNG, JPG, JPEG, WebP. |

---

### Optional Arguments

| Option | Default | Description |
| --- | --- | --- |
| `-t`, `--template` | `stock_logo.bin` | Original stock logo file used as the template. |
| `-o`, `--output` | `logo.bin` | Output file name. |
| `--slot` | `0` | Slot index to replace. Use `all` to replace all compatible fullscreen slots. |
| `--width` | `720` | Target logo width in pixels. |
| `--height` | `1612` | Target logo height in pixels. |
| `--mode` | `auto` | Raw image format used inside the logo. |
| `--resize` | `contain` | How the input image should be resized. |
| `--allow-bigger` | disabled | Allows generating a file larger than the original. Not recommended. |

---

## Raw Image Modes

The `--mode` option controls how the image is converted before compression.

| Mode | Description |
| --- | --- |
| `auto` | Tries to detect the correct format from the original slot size. Recommended. |
| `rgb888` | 24-bit RGB. |
| `bgr888` | 24-bit BGR. |
| `bgra8888` | 32-bit BGRA. |
| `rgba8888` | 32-bit RGBA. |
| `rgb565le` | 16-bit RGB565 little-endian. |

Recommended default:

```bash
--mode auto
```

If auto-detection fails, try:

```bash
--mode rgb565le
```

or:

```bash
--mode rgb888
```

---

## Resize Modes

The `--resize` option controls how your image is adapted to the target resolution.

| Mode | Description |
| --- | --- |
| `contain` | Keeps the full image visible. Adds black background if needed. Recommended. |
| `cover` | Fills the whole screen and crops overflowing areas. |
| `stretch` | Forces the image to the exact size, even if it gets distorted. |

Recommended default:

```bash
--resize contain
```

---

## Examples

### Replace the default slot

```bash
python main.py image.png
```

Output:

```text
logo.bin
```

---

### Use a custom template file

```bash
python main.py image.png --template original_logo.bin
```

---

### Use a custom output file

```bash
python main.py image.png --output custom_logo.bin
```

---

### Replace slot 1

```bash
python main.py image.png --slot 1
```

---

### Replace all compatible fullscreen slots

```bash
python main.py image.png --slot all
```

---

### Use cover resize mode

```bash
python main.py image.png --resize cover
```

---

### Use RGB565 manually

```bash
python main.py image.png --mode rgb565le
```

---

### Use a different resolution

```bash
python main.py image.png --width 720 --height 1600
```

---

### Allow output bigger than the original

```bash
python main.py image.png --allow-bigger
```

> This is not recommended unless you know your device can safely handle a larger logo partition payload.

---

## Recommended Workflow

1. Dump or obtain your original logo partition.
2. Rename it to:

```text
stock_logo.bin
```

3. Put your custom image in the same folder.
4. Run:

```bash
python main.py image.png
```

5. If successful, flash the generated file:

```bash
fastboot flash logo logo.bin
fastboot reboot
```

---

## Troubleshooting

### `The file is too small to be a valid MTK logo.bin`

The file passed as `stock_logo.bin` is probably not a valid MTK logo image or is incomplete.

---

### `LOGO signature was not found at offset 0x08`

The script did not find the expected `LOGO` signature. It will still try to parse the file, but the template may not be compatible.

---

### `Could not infer the slot format`

The script could not detect the raw image format automatically.

Try specifying the mode manually:

```bash
python main.py image.png --mode rgb565le
```

or:

```bash
python main.py image.png --mode rgb888
```

Also make sure the width and height are correct:

```bash
python main.py image.png --width 720 --height 1612
```

---

### `The new logo.bin is bigger than the original one`

The compressed custom image is larger than the original logo payload.

Try one of these options:

- Use a simpler image.
- Use a darker image.
- Reduce visual noise or gradients.
- Try another resize mode.
- Use `--allow-bigger` only if you know what you are doing.

---

### The logo looks distorted

Try changing the resize mode:

```bash
python main.py image.png --resize contain
```

or:

```bash
python main.py image.png --resize cover
```

Avoid `stretch` unless you intentionally want the image to be forced into the screen size.

---

### The logo colors look wrong

Try another raw format:

```bash
python main.py image.png --mode bgr888
```

or:

```bash
python main.py image.png --mode bgra8888
```

or:

```bash
python main.py image.png --mode rgb565le
```

---

## Safety Notes

- Always keep a backup of the original `stock_logo.bin`.
- Do not use a template from a different device unless you know it is compatible.
- Do not flash a file larger than the original unless you fully understand the risk.
- Make sure the generated `logo.bin` matches the expected partition size or payload behavior for your device.
- If possible, test with a simple image first.

---

## License

Use this script at your own risk. No warranty is provided.
