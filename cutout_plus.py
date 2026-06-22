import os
import sys
from pathlib import Path
from collections import deque
from PIL import Image, ImageFilter
from tqdm import tqdm


# =========================
# 基础配置
# =========================

INPUT_DIR = "input_images"
OUTPUT_DIR = "output_cutouts"

# 推荐：
# "chroma_magenta"  删除洋红色背景 #FF00FF，最适合后续游戏素材
# "chroma_green"    删除绿色背景 #00FF00
# "black_bg_safe"   删除纯黑背景，适合你现在这类黑底图
DEFAULT_MODE = "chroma_magenta"
MODE = os.environ.get("CUTOUT_PLUS_MODE", DEFAULT_MODE)
if len(sys.argv) > 1:
    MODE = sys.argv[1]
MODE = MODE.strip()

SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]


# =========================
# 模式预设
# =========================

MODE_CONFIGS = {
    "chroma_magenta": {
        "target_color": (255, 0, 255),
        "tolerance": 35,
        "only_edge_connected": True,
        "auto_crop": True,
        "add_padding": True,
        "padding": 30,
        "resize_output": False,
        "target_size": (768, 1024),
        "soften_alpha_edge": True,
    },

    "chroma_green": {
        "target_color": (0, 255, 0),
        "tolerance": 35,
        "only_edge_connected": True,
        "auto_crop": True,
        "add_padding": True,
        "padding": 30,
        "resize_output": False,
        "target_size": (768, 1024),
        "soften_alpha_edge": True,
    },

    "black_bg_safe": {
        "target_color": (0, 0, 0),
        "tolerance": 18,
        "only_edge_connected": True,
        "auto_crop": True,
        "add_padding": True,
        "padding": 30,
        "resize_output": False,
        "target_size": (768, 1024),
        "soften_alpha_edge": False,
    },
}


def fix_console_encoding():
    """
    修复 Windows 控制台中文乱码。
    """
    if sys.platform.startswith("win"):
        os.system("chcp 65001 > nul")

    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_config():
    if MODE not in MODE_CONFIGS:
        raise ValueError(f"未知模式：{MODE}，可选模式：{list(MODE_CONFIGS.keys())}")

    return MODE_CONFIGS[MODE]


def color_distance(c1, c2):
    """
    计算两个 RGB 颜色之间的距离。
    """
    r1, g1, b1 = c1
    r2, g2, b2 = c2

    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


def is_target_color(pixel, target_color, tolerance):
    """
    判断像素是否接近目标背景色。
    """
    r, g, b, a = pixel

    if a == 0:
        return False

    return color_distance((r, g, b), target_color) <= tolerance


def remove_edge_connected_color(image: Image.Image, config: dict) -> Image.Image:
    """
    只删除和图片边缘连通的目标颜色区域。

    重点：
    不是全图删除目标色，而是从四周边缘开始扩散。
    这样角色内部的相近颜色不会被误删。
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size

    target_color = config["target_color"]
    tolerance = config["tolerance"]

    visited = set()
    queue = deque()

    # 上下边缘作为起点
    for x in range(width):
        for y in [0, height - 1]:
            if is_target_color(pixels[x, y], target_color, tolerance):
                queue.append((x, y))
                visited.add((x, y))

    # 左右边缘作为起点
    for y in range(height):
        for x in [0, width - 1]:
            if is_target_color(pixels[x, y], target_color, tolerance):
                queue.append((x, y))
                visited.add((x, y))

    # BFS 泛洪填充，只删除连通背景
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
                    if is_target_color(pixels[nx, ny], target_color, tolerance):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

    return image


def remove_all_target_color(image: Image.Image, config: dict) -> Image.Image:
    """
    全图删除目标颜色。
    一般不建议给角色用，可能会误删角色内部相近颜色。
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size

    target_color = config["target_color"]
    tolerance = config["tolerance"]

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]

            if is_target_color((r, g, b, a), target_color, tolerance):
                pixels[x, y] = (r, g, b, 0)

    return image


def crop_transparent_area(image: Image.Image) -> Image.Image:
    """
    自动裁剪透明边缘。
    """
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()

    if bbox:
        return image.crop(bbox)

    return image


def add_padding(image: Image.Image, padding: int) -> Image.Image:
    """
    增加透明边距。
    """
    image = image.convert("RGBA")

    new_image = Image.new(
        "RGBA",
        (image.width + padding * 2, image.height + padding * 2),
        (0, 0, 0, 0)
    )

    new_image.paste(image, (padding, padding), image)
    return new_image


def soften_alpha(image: Image.Image) -> Image.Image:
    """
    轻微柔化透明边缘。
    黑底图不建议开太强，否则黑色描边会变虚。
    """
    image = image.convert("RGBA")
    r, g, b, a = image.split()

    a = a.filter(ImageFilter.GaussianBlur(radius=0.35))

    return Image.merge("RGBA", (r, g, b, a))


def resize_keep_ratio(image: Image.Image, target_size) -> Image.Image:
    """
    等比例放进指定透明画布。
    """
    image = image.convert("RGBA")
    image.thumbnail(target_size, Image.LANCZOS)

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))

    x = (target_size[0] - image.width) // 2
    y = (target_size[1] - image.height) // 2

    canvas.paste(image, (x, y), image)
    return canvas


def cutout_image(input_path: Path, output_path: Path, config: dict):
    """
    单张图片处理。
    """
    with Image.open(input_path) as img:
        result = img.convert("RGBA")

        if config["only_edge_connected"]:
            result = remove_edge_connected_color(result, config)
        else:
            result = remove_all_target_color(result, config)

        if config["soften_alpha_edge"]:
            result = soften_alpha(result)

        if config["auto_crop"]:
            result = crop_transparent_area(result)

        if config["add_padding"]:
            result = add_padding(result, config["padding"])

        if config["resize_output"]:
            result = resize_keep_ratio(result, config["target_size"])

        result.save(output_path, "PNG")


def main():
    fix_console_encoding()

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

    for image_file in tqdm(image_files, desc="Processing", ascii=True):
        output_name = image_file.stem + f"_{MODE}_cutout.png"
        output_path = output_dir / output_name

        try:
            cutout_image(image_file, output_path, config)
        except Exception as e:
            print(f"处理失败：{image_file.name}，错误：{e}")

    print("全部处理完成！")
    print(f"输出文件夹：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
