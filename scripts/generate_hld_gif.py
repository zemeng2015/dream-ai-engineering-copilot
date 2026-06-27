# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

WIDTH = 640
HEIGHT = 360
SCALE = 2
DELAY = 65
PALETTE = [
    (248, 250, 252),  # 0 bg
    (15, 23, 42),  # 1 ink
    (219, 234, 254),  # 2 box
    (20, 184, 166),  # 3 highlight
    (14, 116, 144),  # 4 arrow
    (226, 232, 240),  # 5 muted
    (241, 245, 249),  # 6 panel
    (99, 102, 241),  # 7 accent
    (255, 255, 255),  # 8 white
    (148, 163, 184),  # 9 gray
    (45, 212, 191),  # 10 bright
    (30, 41, 59),  # 11 navy
    (186, 230, 253),  # 12 sky
    (209, 250, 229),  # 13 mint
    (254, 243, 199),  # 14 amber
    (252, 231, 243),  # 15 pink
]

FONT = {
    " ": ["00000"] * 7,
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "&": ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "11100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


def new_frame() -> list[int]:
    return [0] * (WIDTH * HEIGHT)


def set_px(frame: list[int], x: int, y: int, color: int) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        frame[y * WIDTH + x] = color


def rect(frame: list[int], x: int, y: int, w: int, h: int, fill: int, outline: int) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            set_px(frame, xx, yy, fill)
    for xx in range(x, x + w):
        set_px(frame, xx, y, outline)
        set_px(frame, xx, y + h - 1, outline)
    for yy in range(y, y + h):
        set_px(frame, x, yy, outline)
        set_px(frame, x + w - 1, yy, outline)


def line(frame: list[int], x0: int, y0: int, x1: int, y1: int, color: int) -> None:
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for ox in (0, 1):
            for oy in (0, 1):
                set_px(frame, x0 + ox, y0 + oy, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def arrow(frame: list[int], x0: int, y0: int, x1: int, y1: int, color: int) -> None:
    line(frame, x0, y0, x1, y1, color)
    if abs(x1 - x0) >= abs(y1 - y0):
        direction = 1 if x1 >= x0 else -1
        line(frame, x1, y1, x1 - 10 * direction, y1 - 6, color)
        line(frame, x1, y1, x1 - 10 * direction, y1 + 6, color)
    else:
        direction = 1 if y1 >= y0 else -1
        line(frame, x1, y1, x1 - 6, y1 - 10 * direction, color)
        line(frame, x1, y1, x1 + 6, y1 - 10 * direction, color)


def text_width(text: str, scale: int = SCALE) -> int:
    return len(text) * 6 * scale - scale


def draw_text(frame: list[int], x: int, y: int, text: str, color: int, scale: int = SCALE) -> None:
    cursor = x
    for char in text.upper():
        glyph = FONT.get(char, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    for sy in range(scale):
                        for sx in range(scale):
                            set_px(frame, cursor + gx * scale + sx, y + gy * scale + sy, color)
        cursor += 6 * scale


def centered_text(frame: list[int], x: int, y: int, w: int, lines: list[str], color: int) -> None:
    total_h = len(lines) * 17 - 3
    cy = y + (52 - total_h) // 2
    for label in lines:
        draw_text(frame, x + (w - text_width(label)) // 2, cy, label, color)
        cy += 17


def draw_box(
    frame: list[int],
    box: tuple[int, int, int, int, list[str]],
    active: bool,
    done: bool,
) -> None:
    x, y, w, h, labels = box
    fill = 13 if active else 2 if done else 6
    outline = 3 if active else 4 if done else 9
    rect(frame, x, y, w, h, fill, outline)
    centered_text(frame, x, y, w, labels, 1)


def draw_frame(step: int) -> list[int]:
    frame = new_frame()
    rect(frame, 18, 18, WIDTH - 36, HEIGHT - 36, 8, 5)
    draw_text(frame, 48, 38, "DREAM GOVERNED MEMORY HLD", 1, scale=2)
    draw_text(frame, 48, 314, "SOURCE BACKED CLAIMS  VALIDATION  REVIEW  OUTPUTS", 4, scale=1)

    boxes = [
        (38, 92, 118, 52, ["SOURCE", "REGISTRY"]),
        (188, 92, 118, 52, ["SOURCE", "SPANS"]),
        (338, 92, 118, 52, ["REPO", "GRAPH"]),
        (488, 92, 118, 52, ["CANDIDATE", "CLAIMS"]),
        (488, 218, 118, 52, ["VALIDATION", "GATES"]),
        (338, 218, 118, 52, ["MEMORY", "REVIEW"]),
        (188, 218, 118, 52, ["MEMORY", "LEDGER"]),
        (38, 218, 118, 52, ["REQ PR", "WIKI EVAL"]),
    ]

    arrows = [
        (156, 118, 188, 118),
        (306, 118, 338, 118),
        (456, 118, 488, 118),
        (547, 144, 547, 218),
        (488, 244, 456, 244),
        (338, 244, 306, 244),
        (188, 244, 156, 244),
    ]
    for index, coords in enumerate(arrows):
        arrow(frame, *coords, 3 if index < step else 9)
    for index, box in enumerate(boxes):
        draw_box(frame, box, active=index == step, done=index < step)
    return frame


def pack_codes(codes: list[int], code_size: int) -> bytes:
    output = bytearray()
    buffer = 0
    bits = 0
    for code in codes:
        buffer |= code << bits
        bits += code_size
        while bits >= 8:
            output.append(buffer & 0xFF)
            buffer >>= 8
            bits -= 8
    if bits:
        output.append(buffer & 0xFF)
    return bytes(output)


def lzw_data(indices: list[int], min_code_size: int = 4) -> bytes:
    clear = 1 << min_code_size
    end = clear + 1
    codes = [clear]
    run = 0
    for value in indices:
        if run >= 10:
            codes.append(clear)
            run = 0
        codes.append(value)
        run += 1
    codes.append(end)
    packed = pack_codes(codes, min_code_size + 1)
    chunks = bytearray([min_code_size])
    for index in range(0, len(packed), 255):
        chunk = packed[index : index + 255]
        chunks.append(len(chunk))
        chunks.extend(chunk)
    chunks.append(0)
    return bytes(chunks)


def write_gif(path: Path, frames: list[list[int]]) -> None:
    data = bytearray()
    data.extend(b"GIF89a")
    data.extend(WIDTH.to_bytes(2, "little"))
    data.extend(HEIGHT.to_bytes(2, "little"))
    data.append(0xF3)
    data.append(0)
    data.append(0)
    for red, green, blue in PALETTE:
        data.extend(bytes([red, green, blue]))
    data.extend(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")
    for frame in frames:
        data.extend(b"\x21\xF9\x04")
        data.append(0x04)
        data.extend(DELAY.to_bytes(2, "little"))
        data.append(0)
        data.append(0)
        data.append(0x2C)
        data.extend((0).to_bytes(2, "little"))
        data.extend((0).to_bytes(2, "little"))
        data.extend(WIDTH.to_bytes(2, "little"))
        data.extend(HEIGHT.to_bytes(2, "little"))
        data.append(0)
        data.extend(lzw_data(frame))
    data.append(0x3B)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(data))


def main() -> None:
    frames = [draw_frame(step) for step in range(8)]
    write_gif(Path("docs/assets/dream-hld.gif"), frames)


if __name__ == "__main__":
    main()
