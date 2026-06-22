import os
import sys
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# =========================
# 基础配置
# =========================

INPUT_DIR = "input_images"
OUTPUT_DIR = "output_cutouts"

# 背景色：洋红色 #FF00FF
TARGET_COLOR = (255, 0, 255)

# 容差：纯洋红背景建议 25~40；边缘有轻微抗锯齿可调到 45~60
TOLERANCE = 35

# 关键开关：保持原图画布大小与素材位置
# True：输出图片尺寸与原图完全一致，角色/物体坐标不变
# False：允许裁剪透明边缘，适合只想得到最小包围盒素材时使用
PRESERVE_CANVAS = True

# 仅当 PRESERVE_CANVAS = False 时生效
AUTO_CROP = True
ADD_PADDING = False
PADDING = 30

# 统一缩放默认关闭。开启后尺寸必然改变。
RESIZE_OUTPUT = False
TARGET_SIZE = (768, 1024)

SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]


def fix_console_encoding():
    if sys.platform.startswith("win"):
        os.system("chcp 65001 > nul")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def remove_magenta_keep_canvas(image: Image.Image, target_color, tolerance) -> Image.Image:
    """
    删除整张图中所有接近 target_color 的像素，但不裁剪、不平移、不缩放。
    输出画布尺寸与输入完全一致，素材位置完全不变。
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    tr, tg, tb = target_color
    tolerance_sq = tolerance * tolerance

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            dist_sq = (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2
            if dist_sq <= tolerance_sq:
                # RGB 顺手清零，避免部分游戏引擎缩放时出现洋红边缘污染
                pixels[x, y] = (0, 0, 0, 0)

    return image


def crop_transparent_area(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox:
        return image.crop(bbox)
    return image


def add_padding(image: Image.Image, padding: int) -> Image.Image:
    image = image.convert("RGBA")
    canvas = Image.new("RGBA", (image.width + padding * 2, image.height + padding * 2), (0, 0, 0, 0))
    canvas.paste(image, (padding, padding), image)
    return canvas


def resize_keep_ratio(image: Image.Image, target_size) -> Image.Image:
    image = image.convert("RGBA")
    image.thumbnail(target_size, Image.LANCZOS)
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    x = (target_size[0] - image.width) // 2
    y = (target_size[1] - image.height) // 2
    canvas.paste(image, (x, y), image)
    return canvas


def cutout_image(input_path: Path, output_path: Path):
    with Image.open(input_path) as img:
        original_size = img.size
        result = remove_magenta_keep_canvas(img, TARGET_COLOR, TOLERANCE)

        if not PRESERVE_CANVAS:
            if AUTO_CROP:
                result = crop_transparent_area(result)
            if ADD_PADDING:
                result = add_padding(result, PADDING)

        if RESIZE_OUTPUT:
            result = resize_keep_ratio(result, TARGET_SIZE)

        # 防止误改：默认模式下强制校验输出尺寸
        if PRESERVE_CANVAS and not RESIZE_OUTPUT and result.size != original_size:
            raise RuntimeError(f"输出尺寸异常：原图 {original_size}，输出 {result.size}")

        result.save(output_path, "PNG")


def main():
    fix_console_encoding()

    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_files = [p for p in input_dir.iterdir() if p.suffix.lower() in SUPPORTED_FORMATS]
    if not image_files:
        print(f"没有找到图片，请把图片放到 {INPUT_DIR} 文件夹里。")
        return

    print("=" * 40)
    print("当前模式：删除所有洋红色，并保持原图尺寸/位置")
    print(f"目标颜色：{TARGET_COLOR}")
    print(f"容差：{TOLERANCE}")
    print(f"保持画布：{PRESERVE_CANVAS}")
    print(f"输入文件夹：{INPUT_DIR}")
    print(f"输出文件夹：{OUTPUT_DIR}")
    print(f"图片数量：{len(image_files)}")
    print("=" * 40)

    for image_file in tqdm(image_files, desc="Processing", ascii=True):
        output_path = output_dir / f"{image_file.stem}_cutout.png"
        try:
            cutout_image(image_file, output_path)
        except Exception as e:
            print(f"处理失败：{image_file.name}，错误：{e}")

    print("全部处理完成！")
    print(f"输出文件夹：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
