# AI 生图洋红背景自动抠图工具

这是一个面向游戏素材生产的批量抠图小工具，特别适合配合 AI 生图使用：先让 AI 生成 `#FF00FF` 纯洋红背景的角色、道具或怪物素材，再用本项目一键删除背景，输出透明 PNG。

项目默认推荐使用“洋红背景 + 保留原画布”的流程。这样导出的素材不会改变原图尺寸和主体坐标，适合后续继续放进游戏、编辑器、UI 图集或自动构图流程里。

## 核心流程

1. 用 AI 生成纯洋红背景素材，背景尽量写明 `#FF00FF`。
2. 把图片放入 `input_images` 文件夹。
3. 双击对应模式的 `.bat` 文件。
4. 在 `output_cutouts` 文件夹获取透明 PNG。

## 推荐入口

最推荐先用：

```text
run_magenta_cutout.bat
```

它会调用 `magenta_preserve_canvas.py`，删除洋红背景，同时默认保留原图画布尺寸和主体位置。对于 AI 生图的游戏素材，这是最稳的入口。

## 每个模式的 bat

| bat 文件 | 作用 | 适合场景 |
| --- | --- | --- |
| `run_magenta_cutout.bat` | 删除洋红背景并保留原画布 | AI 生图游戏素材，推荐 |
| `run_chroma_magenta.bat` | 删除洋红背景 | 普通洋红色键抠图 |
| `run_chroma_green.bat` | 删除绿色背景 | 绿幕素材 |
| `run_black_bg_safe.bat` | 删除黑色背景 | 黑底图、黑色背景素材 |
| `run_auto_character.bat` | AI 自动抠角色 | 白底或复杂背景角色立绘 |
| `run_auto_item.bat` | AI 自动抠道具 | 道具图标，输出 `256x256` |
| `run_auto_monster.bat` | AI 自动抠怪物 | 怪物 / Boss，输出 `1024x1024` |
| `run_auto_aggressive.bat` | 强力去白底 | 背景很白、主体白色细节少 |
| `run_auto_safe.bat` | 保守去白底 | 减少误删主体细节 |

双击 bat 前，只需要把要处理的图片放进 `input_images`。

## AI 生图提示词样例

关键点是：纯洋红背景、主体完整、居中、不要阴影、不要地面、不要文字水印。

### 角色立绘

```text
一名幻想风游戏角色，全身立绘，居中构图，完整身体，不裁切，清晰轮廓，干净边缘，2D game character sprite，纯洋红色背景 #FF00FF，无阴影，无地面，无文字，无水印
```

### 道具图标

```text
单个魔法药水瓶道具图标，游戏 UI 图标风格，物体居中，完整物体，四周留白，清晰边缘，纯洋红色背景 #FF00FF，无阴影，无文字，无水印
```

### 怪物 / Boss

```text
一只幻想风 Boss 怪物，全身，正面或四分之三视角，主体居中，轮廓清晰，完整身体，不裁切，纯洋红色背景 #FF00FF，无地面阴影，无场景背景，无文字，无水印
```

### 英文辅助词

```text
pure solid magenta background (#FF00FF), centered subject, full body, clean silhouette, sharp edges, no shadow, no floor, no text, no watermark, no background details
```

### 负面提示词

```text
复杂背景，渐变背景，透明背景，阴影，地面，裁切，多个主体，文字，水印，边缘发光，半透明烟雾，背景装饰
```

## 命令行用法

如果不想双击 bat，也可以直接传模式：

```bash
python cutout_plus.py chroma_magenta
python cutout_plus.py chroma_green
python cutout_plus.py black_bg_safe
```

```bash
python auto_cutout.py character
python auto_cutout.py item
python auto_cutout.py monster
python auto_cutout.py aggressive
python auto_cutout.py safe
```

## 依赖安装

基础色键抠图需要：

```bash
python -m pip install pillow tqdm
```

使用 `auto_cutout.py` 的 AI 自动抠图模式还需要：

```bash
python -m pip install rembg
```

bat 会自动检查并尝试安装对应依赖。

## 项目结构

```text
.
├─ input_images/              # 放入待处理图片
├─ output_cutouts/            # 输出透明 PNG
├─ magenta_preserve_canvas.py # 洋红背景抠图，保留原图画布，推荐入口
├─ cutout_plus.py             # 多色键抠图：洋红、绿幕、黑底
├─ auto_cutout.py             # rembg 自动抠图 + 白底清理
├─ magenta.py                 # 简版洋红背景抠图
└─ *.bat                      # 各模式一键运行入口
```

## 常用配置

### `magenta_preserve_canvas.py`

```python
TARGET_COLOR = (255, 0, 255)
TOLERANCE = 35
PRESERVE_CANVAS = True
```

- `TARGET_COLOR`：要删除的背景色，默认是洋红 `#FF00FF`。
- `TOLERANCE`：颜色容差。背景边缘有抗锯齿时可以调高。
- `PRESERVE_CANVAS`：是否保留原图画布尺寸和主体坐标。游戏素材建议保持 `True`。

### `cutout_plus.py`

```python
DEFAULT_MODE = "chroma_magenta"
```

可选模式：`chroma_magenta`、`chroma_green`、`black_bg_safe`。

### `auto_cutout.py`

```python
DEFAULT_MODE = "item"
```

可选模式：`character`、`item`、`monster`、`aggressive`、`safe`。

## 输出规则

- `magenta_preserve_canvas.py`：输出为 `原文件名_cutout.png`。
- `cutout_plus.py`：输出为 `原文件名_MODE_cutout.png`。
- `auto_cutout.py`：输出为 `原文件名.png`。
- 所有结果都会保存到 `output_cutouts`。

## 常见问题

### 输出图还有一圈洋红色

把 `TOLERANCE` 适当调高，例如从 `35` 改成 `45` 或 `60`。

### 主体被误删

把 `TOLERANCE` 调低。AI 自动抠图可以尝试 `run_auto_safe.bat`。

### bat 提示找不到 Python

安装 Python，并在安装时勾选 `Add Python to PATH`。

### 中文显示乱码

项目文件按 UTF-8 保存。Windows 终端如果显示异常，可以优先双击 bat 运行，bat 内部已经切换到 UTF-8 代码页。
