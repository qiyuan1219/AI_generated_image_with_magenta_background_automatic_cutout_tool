import os
import sys
from pathlib import Path
from PIL import Image, ImageFilter
from tqdm import tqdm


# =========================
# 基础配置
# =========================

INPUT_DIR = "input_images"
OUTPUT_DIR = "output_cutouts"

# 背景色：洋红色 #FF00FF
TARGET_COLOR = (255, 0, 255)

# 容差：越大越容易把“接近洋红”的颜色也删掉
# 如果你的图背景非常纯，可以设 20~30
# 如果背景边缘有抗锯齿、渐变，可以设 35~50
TOLERANCE = 35

# 是否自动裁剪透明边缘
AUTO_CROP = True

# 是否增加透明边距
ADD_PADDING = True
PADDING = 30

# 是否统一缩放
RESIZE_OUTPUT = False
TARGET_SIZE = (768, 1024)

# 是否柔化透明边缘
SOFTEN_ALPHA_EDGE = True

SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]


# =========================
# 控制台防乱码
# =========================

def fix_console_encoding():
    if sys.platform.startswith("win"):
        os.system("chcp 65001 > nul")

    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# =========================
# 核心函数
# =========================

def color_distance(c1, c2):
    """
    计算两个 RGB 颜色之间的欧氏距离
    """
    r1, g1, b1 = c1
    r2, g2, b2 = c2
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


def is_target_color(pixel, target_color, tolerance):
    """
    判断像素是否接近目标颜色
    """
    r, g, b, a = pixel

    if a == 0:
        return False

    return color_distance((r, g, b), target_color) <= tolerance


def remove_all_target_color(image: Image.Image, target_color, tolerance) -> Image.Image:
    """
    删除整张图中所有接近 target_color 的像素
    不管它在边缘还是内部，全部设为透明
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]

            if is_target_color((r, g, b, a), target_color, tolerance):
                pixels[x, y] = (r, g, b, 0)

    return image


def crop_transparent_area(image: Image.Image) -> Image.Image:
    """
    裁剪掉外围透明区域
    """
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()

    if bbox:
        return image.crop(bbox)

    return image


def add_padding(image: Image.Image, padding: int) -> Image.Image:
    """
    给图像四周加透明边距
    """
    image = image.convert("RGBA")

    new_width = image.width + padding * 2
    new_height = image.height + padding * 2

    new_image = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    new_image.paste(image, (padding, padding), image)

    return new_image


def soften_alpha(image: Image.Image) -> Image.Image:
    """
    稍微柔化透明边缘，让抠图更自然
    """
    image = image.convert("RGBA")
    r, g, b, a = image.split()

    a = a.filter(ImageFilter.GaussianBlur(radius=0.35))

    return Image.merge("RGBA", (r, g, b, a))


def resize_keep_ratio(image: Image.Image, target_size) -> Image.Image:
    """
    等比例缩放到指定画布中
    """
    image = image.convert("RGBA")
    image.thumbnail(target_size, Image.LANCZOS)

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))

    x = (target_size[0] - image.width) // 2
    y = (target_size[1] - image.height) // 2

    canvas.paste(image, (x, y), image)
    return canvas


def cutout_image(input_path: Path, output_path: Path):
    """
    单张图片处理流程
    """
    with Image.open(input_path) as img:
        result = img.convert("RGBA")

        # 1. 删除所有洋红色
        result = remove_all_target_color(result, TARGET_COLOR, TOLERANCE)

        # 2. 柔化边缘
        if SOFTEN_ALPHA_EDGE:
            result = soften_alpha(result)

        # 3. 裁剪透明边缘
        if AUTO_CROP:
            result = crop_transparent_area(result)

        # 4. 添加透明边距
        if ADD_PADDING:
            result = add_padding(result, PADDING)

        # 5. 缩放
        if RESIZE_OUTPUT:
            result = resize_keep_ratio(result, TARGET_SIZE)

        result.save(output_path, "PNG")


def main():
    fix_console_encoding()

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
    print("当前模式：删除所有洋红色")
    print(f"目标颜色：{TARGET_COLOR}")
    print(f"容差：{TOLERANCE}")
    print(f"输入文件夹：{INPUT_DIR}")
    print(f"输出文件夹：{OUTPUT_DIR}")
    print(f"图片数量：{len(image_files)}")
    print("=" * 40)

    for image_file in tqdm(image_files, desc="Processing", ascii=True):
        output_name = image_file.stem + "_cutout.png"
        output_path = output_dir / output_name

        try:
            cutout_image(image_file, output_path)
        except Exception as e:
            print(f"处理失败：{image_file.name}，错误：{e}")

    print("全部处理完成！")
    print(f"输出文件夹：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()