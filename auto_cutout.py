

import os
import sys
import contextlib
from pathlib import Path
from PIL import Image, ImageFilter
from rembg import remove
from tqdm import tqdm
from collections import deque

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["OMP_NUM_THREADS"] = "1"

if sys.platform.startswith("win"):
    os.system("chcp 65001 > nul")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
# =========================
# 只需要改这里
# =========================

INPUT_DIR = "input_images"
OUTPUT_DIR = "output_cutouts"

# 可选：
# "character"   角色立绘，推荐默认
# "item"        道具图标
# "monster"     怪物 / Boss
# "aggressive"  强力抠白
# "safe"        保守抠图
DEFAULT_MODE = "item"
MODE = os.environ.get("AUTO_CUTOUT_MODE", DEFAULT_MODE)
if len(sys.argv) > 1:
    MODE = sys.argv[1]
MODE = MODE.strip()


SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]


# =========================
# 模式预设
# =========================

MODE_CONFIGS = {
    "character": {
        "auto_crop": True,
        "add_padding": True,
        "padding": 40,
        "resize_output": True,
        "target_size": (768, 1024),

        "rembg_pass_count": 2,
        "remove_white_background": True,
        "white_threshold": 230,
        "white_color_tolerance": 30,
        "only_edge_connected_white": True,

        "remove_white_edge": True,
        "white_edge_strength": 0.65,
        "soften_alpha_edge": True,
    },

    "item": {
        "auto_crop": True,
        "add_padding": True,
        "padding": 20,
        "resize_output": True,
        "target_size": (256, 256),

        "rembg_pass_count": 2,
        "remove_white_background": True,
        "white_threshold": 225,
        "white_color_tolerance": 35,
        "only_edge_connected_white": True,

        "remove_white_edge": True,
        "white_edge_strength": 0.75,
        "soften_alpha_edge": True,
    },

    "monster": {
        "auto_crop": True,
        "add_padding": True,
        "padding": 60,
        "resize_output": True,
        "target_size": (1024, 1024),

        "rembg_pass_count": 2,
        "remove_white_background": True,
        "white_threshold": 230,
        "white_color_tolerance": 32,
        "only_edge_connected_white": True,

        "remove_white_edge": True,
        "white_edge_strength": 0.7,
        "soften_alpha_edge": True,
    },

    "aggressive": {
        "auto_crop": True,
        "add_padding": True,
        "padding": 30,
        "resize_output": False,
        "target_size": (768, 1024),

        "rembg_pass_count": 3,
        "remove_white_background": True,
        "white_threshold": 215,
        "white_color_tolerance": 45,
        "only_edge_connected_white": False,

        "remove_white_edge": True,
        "white_edge_strength": 0.85,
        "soften_alpha_edge": True,
    },

    "safe": {
        "auto_crop": True,
        "add_padding": True,
        "padding": 40,
        "resize_output": False,
        "target_size": (768, 1024),

        "rembg_pass_count": 1,
        "remove_white_background": True,
        "white_threshold": 245,
        "white_color_tolerance": 18,
        "only_edge_connected_white": True,

        "remove_white_edge": True,
        "white_edge_strength": 0.45,
        "soften_alpha_edge": True,
    },
}


def get_config():
    if MODE not in MODE_CONFIGS:
        print(f"未知模式：{MODE}")
        print(f"可用模式：{list(MODE_CONFIGS.keys())}")
        raise ValueError(f"未知模式：{MODE}")

    return MODE_CONFIGS[MODE]


def is_near_white(pixel, threshold, tolerance):
    """
    判断像素是否接近白色 / 浅灰 / 米白
    """
    r, g, b, a = pixel

    if a == 0:
        return False

    bright_enough = r >= threshold and g >= threshold and b >= threshold

    color_close = (
        abs(r - g) <= tolerance and
        abs(r - b) <= tolerance and
        abs(g - b) <= tolerance
    )

    return bright_enough and color_close


def remove_edge_connected_white(image: Image.Image, config: dict) -> Image.Image:
    """
    只删除和图片边缘连通的白色背景。
    适合角色立绘，能减少误删白衣服、白头发、眼白、高光。
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size

    visited = set()
    queue = deque()

    threshold = config["white_threshold"]
    tolerance = config["white_color_tolerance"]

    # 上下边缘
    for x in range(width):
        for y in [0, height - 1]:
            if is_near_white(pixels[x, y], threshold, tolerance):
                queue.append((x, y))
                visited.add((x, y))

    # 左右边缘
    for y in range(height):
        for x in [0, width - 1]:
            if is_near_white(pixels[x, y], threshold, tolerance):
                queue.append((x, y))
                visited.add((x, y))

    while queue:
        x, y = queue.popleft()

        r, g, b, a = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)

        for nx, ny in [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]:
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited:
                    if is_near_white(pixels[nx, ny], threshold, tolerance):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

    return image


def remove_all_near_white(image: Image.Image, config: dict) -> Image.Image:
    """
    删除全图接近白色的像素。
    aggressive 模式会用到，适合背景很白、主体没有白色细节的图。
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size

    threshold = config["white_threshold"]
    tolerance = config["white_color_tolerance"]

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]

            if is_near_white((r, g, b, a), threshold, tolerance):
                pixels[x, y] = (r, g, b, 0)

    return image


def clean_white_edge(image: Image.Image, config: dict) -> Image.Image:
    """
    清理主体边缘残留白边。
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size

    strength = config["white_edge_strength"]

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]

            if a == 0:
                continue

            is_semi_transparent = a < 230
            is_white_edge = r > 200 and g > 200 and b > 200

            if is_semi_transparent and is_white_edge:
                new_alpha = int(a * (1 - strength))
                pixels[x, y] = (r, g, b, max(0, new_alpha))

    return image


def soften_alpha(image: Image.Image) -> Image.Image:
    """
    轻微柔化透明边缘。
    """
    image = image.convert("RGBA")
    r, g, b, a = image.split()

    a = a.filter(ImageFilter.GaussianBlur(radius=0.4))

    return Image.merge("RGBA", (r, g, b, a))


def crop_transparent_area(image: Image.Image) -> Image.Image:
    """
    裁剪透明区域。
    """
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()

    if bbox:
        return image.crop(bbox)

    return image


def add_padding(image: Image.Image, padding: int) -> Image.Image:
    """
    添加透明边距。
    """
    image = image.convert("RGBA")

    new_width = image.width + padding * 2
    new_height = image.height + padding * 2

    new_image = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    new_image.paste(image, (padding, padding), image)

    return new_image


def resize_keep_ratio(image: Image.Image, target_size) -> Image.Image:
    """
    等比例缩放到目标画布内。
    """
    image = image.convert("RGBA")
    image.thumbnail(target_size, Image.LANCZOS)

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))

    x = (target_size[0] - image.width) // 2
    y = (target_size[1] - image.height) // 2

    canvas.paste(image, (x, y), image)

    return canvas

def silent_rembg_remove(image: Image.Image) -> Image.Image:
    """
    静默调用 rembg，屏蔽 onnxruntime / rembg 的底层乱码输出
    """
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            return remove(image)
def remove_background(input_path: Path, output_path: Path, config: dict):
    """
    单张图片抠图流程。
    """
    with Image.open(input_path) as img:
        cutout = img.convert("RGBA")

        # 1. rembg 多轮抠图
        for _ in range(config["rembg_pass_count"]):
            cutout = silent_rembg_remove(cutout)
            cutout = cutout.convert("RGBA")

        # 2. 删除白色背景
        if config["remove_white_background"]:
            if config["only_edge_connected_white"]:
                cutout = remove_edge_connected_white(cutout, config)
            else:
                cutout = remove_all_near_white(cutout, config)

        # 3. 清理白边
        if config["remove_white_edge"]:
            cutout = clean_white_edge(cutout, config)

        # 4. 柔化边缘
        if config["soften_alpha_edge"]:
            cutout = soften_alpha(cutout)

        # 5. 自动裁剪
        if config["auto_crop"]:
            cutout = crop_transparent_area(cutout)

        # 6. 添加边距
        if config["add_padding"]:
            cutout = add_padding(cutout, config["padding"])

        # 7. 统一尺寸
        if config["resize_output"]:
            cutout = resize_keep_ratio(cutout, config["target_size"])

        cutout.save(output_path, "PNG")


def main():
    config = get_config()

    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_files = [
        file for file in input_dir.iterdir()
        if file.suffix.lower() in SUPPORTED_FORMATS
    ]

    if not image_files:
        print(f"没有找到图片，请把图片放到 {INPUT_DIR} 文件夹里。")
        return

    print("=" * 40)
    print(f"当前模式：{MODE}")
    print(f"输入文件夹：{INPUT_DIR}")
    print(f"输出文件夹：{OUTPUT_DIR}")
    print(f"图片数量：{len(image_files)}")
    print("=" * 40)

    for image_file in tqdm(image_files, desc="正在抠图"):
        output_name = image_file.stem + f".png"
        output_path = output_dir / output_name

        try:
            remove_background(image_file, output_path, config)
        except Exception as e:
            print(f"处理失败：{image_file.name}，错误：{e}")

    print("全部处理完成！")
    print(f"输出文件夹：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
