# YoloToJson v1.0.0.1

YOLO 标注格式转 LabelMe JSON 格式的桌面工具，提供图形化交互界面，支持单文件与批量转换，默认中文界面，可切换英文。

## 功能概览

| 功能 | 说明 |
|------|------|
| 单文件转换 | 选择一个 `.txt` 文件 + 对应图像，输出一个 `.json` 文件 |
| 批量转换 | 选择一个包含 `.txt` 文件的文件夹，批量转换为 `.json` |
| 类别名称映射 | 编辑 Class ID → 类别名称的对应关系，支持 CSV 导入/导出 |
| 输出配置 | 指定 JSON 输出目录，支持文件冲突策略（覆盖/跳过） |
| 打开输出目录 | 转换完成后一键在资源管理器中打开 JSON 输出文件夹 |
| 取消转换 | 批量转换过程中可随时中止 |
| 中英切换 | 菜单栏 语言 → 中文 / English，实时切换界面语言 |
| 版本信息 | 窗口标题栏、关于对话框、.exe 文件属性中显示 `1.0.0.1` |
| 设置持久化 | 上次使用的路径、类别名称、窗口大小等自动保存为 `config.ini` |

## 系统要求

- Windows 10 / 11
- 64 位操作系统
- 独立 `.exe` 无需安装 Python

## 快速开始

### 方式一：运行 .exe（推荐）

直接双击 `dist/YoloToJson.exe` 启动。

右键 `.exe` → 属性 → 详细信息，可查看版本号 `1.0.0.1`。

### 方式二：Python 源码运行

```bash
pip install Pillow
python main.py
```

## 使用流程

1. 选择模式：单文件 或 批量文件夹
2. 选择 YOLO `.txt` 文件（或文件夹）
3. 选择对应的图像文件夹
4. 编辑类别名称映射表（Class ID → 类别名称）
5. 指定 JSON 输出目录
6. 点击 **开始转换**
7. 转换完成后点击 **打开输出目录** 查看结果

## 界面布局

```
┌──────────────┬──────────────────────┐
│  输入配置     │                      │
│  - 模式选择   │                      │
│  - .txt 源    │    转换日志           │
│  - 图像目录   │                      │
├──────────────┤                      │
│  类别名称映射 │                      │
│  - 添加/删除  │                      │
│  - 导入/导出  │                      │
├──────────────┴──────────────────────┤
│  输出配置                            │
│  - 输出目录 / 文件冲突策略            │
├─────────────────────────────────────┤
│  [开始转换] [取消] [打开输出目录]      │
│  ████████████░░░░░░ 进度条            │
├─────────────────────────────────────┤
│  就绪                                │
└─────────────────────────────────────┘
```

## 标注格式

### YOLO 格式（输入）

每行一个目标，空格分隔的归一化坐标：

```
class_id x_center y_center width height
```

所有坐标值为归一化值（0~1），相对于图像宽度和高度。

示例（`test.txt`）：
```
0 0.5 0.5 0.3 0.4
1 0.2 0.3 0.1 0.15
```

### LabelMe JSON 格式（输出）

```json
{
  "version": "4.5.6",
  "flags": {},
  "shapes": [
    {
      "label": "defect",
      "points": [[224, 144], [416, 144], [416, 336], [224, 336]],
      "group_id": null,
      "shape_type": "rectangle",
      "flags": {}
    }
  ],
  "imagePath": "test.jpg",
  "imageData": null,
  "imageHeight": 480,
  "imageWidth": 640
}
```

## 支持的图像格式

`.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.tif`

图像文件名必须与 `.txt` 文件名一致（大小写自动适配）。例如 `image001.txt` 会匹配 `image001.jpg`、`image001.JPG`、`image001.png` 等。

## 项目结构

```
Yolo_to_json/
├── main.py                # GUI 主程序 (tkinter), VERSION 常量
├── yolo_to_json.py         # 核心转换逻辑 (YOLO → LabelMe JSON)
├── converter_worker.py     # 后台线程工作器 (非阻塞转换)
├── settings_manager.py     # 配置持久化 (config.ini, 默认类别 defect)
├── lang.py                 # 中英双语 i18n 模块 (>100 条翻译)
├── build.spec              # PyInstaller 打包配置 (含版本信息)
├── version_info.txt        # Windows VSVersionInfo (1.0.0.1)
├── requirements.txt        # Python 依赖 (Pillow, pyinstaller)
├── .vscode/                # VS Code 调试配置
│   ├── launch.json         # 4 种调试模式 (F5 启动)
│   └── settings.json       # Python 解释器路径
├── dist/
│   └── YoloToJson.exe      # 独立可执行文件 (约 19 MB)
└── README.md
```

## 构建 .exe

```bash
pip install Pillow pyinstaller
python -m PyInstaller build.spec --noconfirm
# 输出: dist/YoloToJson.exe (含版本信息 1.0.0.1)
```

## 调试

VS Code 打开项目文件夹，按 `F5` 选择 **Launch YoloToJson (main.py)** 启动调试。

调试配置文件：`.vscode/launch.json`，已预配 `cwd` 和 Python 解释器路径。

## 技术架构

| 层 | 技术 |
|----|------|
| GUI | tkinter (Python 标准库) |
| 图像读取 | Pillow (PIL) |
| 后台线程 | threading + queue.Queue |
| 国际化 | 自研 i18n 模块 (lang.py) |
| 打包 | PyInstaller 6.x |
| 主题 | 亮色简洁风格 (白色/浅灰) |

## 许可

内部工具，无许可证限制。
