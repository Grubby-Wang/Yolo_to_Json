# 项目结构说明（YoloToJson v1.3.3.0）

> 本文由接管时的实测结果整理，不是对 README 的复述。所有行号对应当前 `master_cr` 分支提交 `d388649`。
> 校验方式见文末「验证基线」。

## 1. 一句话定位

tkinter 桌面工具，把 YOLO 检测标注（`class_id cx cy w h`，归一化）转换成 LabelMe JSON；
附带两个独立工具窗口：**图像裁切** 与 **YOLO 标注**。纯 Python，唯一第三方依赖 Pillow，
用 PyInstaller 打包成单文件 `YoloToJson.exe`（约 29.7 MB，无控制台）。

| 项 | 实际值（已实测） |
|---|---|
| 版本 | `1.3.3.0`，`main.py:31` 为唯一代码源 |
| Python | 3.14.4（`C:\Python314\python.exe`） |
| Pillow | 12.2.0 |
| PyInstaller | 6.20.0 |
| GUI | tkinter + ttk（`clam` 主题） |
| 分支 | `master_cr`（与 `origin/master_cr` 同步），另有 `main` |
| 代码量 | 12 个模块，共 4260 行 |
| 自动化测试 | **0 个**（仓库内不存在测试文件） |

## 2. 目录结构

```
Yolo_to_json/
├── main.py                 821 行  主窗口 + 应用装配 + 转换生命周期
├── converter_worker.py     148 行  后台转换线程（queue → 主线程回调）
├── yolo_to_json.py         240 行  转换核心逻辑（无 GUI 依赖）
├── settings_manager.py     233 行  config.ini 持久化（configparser）
├── lang.py                 292 行  i18n：180 条中英文案 + tr()
├── class_manager.py        300 行  类别映射表格组件（主窗口/标注器共用）
├── viewer_base.py          286 行  图像浏览基类（缩放/导航/坐标换算）
├── cropper_window.py       599 行  裁切工具窗口
├── image_cropper.py        157 行  裁切核心逻辑 + Region 归一化矩形
├── annotator_window.py    1028 行  标注工具窗口（框编辑/撤销/列表/筛选/删除）
├── yolo_annotation.py      114 行  YOLO txt 读写 + classes.txt
├── ui_theme.py              42 行  颜色/字体/调色板常量
├── build.spec                     PyInstaller 配置（hiddenimports 手写清单）
├── version_info.txt               Windows 版本资源（1.3.3.0）
├── requirements.txt               Pillow, pyinstaller
├── config.ini                     运行期生成的用户配置（.gitignore，未入库）
├── icon/                           main_label.ico / main_label.png（打包用）
├── docs/                           本次新增：结构说明与优化清单
├── .vscode/                        launch.json（4 种调试）、settings.json
├── build/                          37 MB PyInstaller 中间产物（.gitignore）
├── dist/                           YoloToJson.exe（.gitignore）
└── __pycache__/                   Python 字节码（.gitignore）
```

## 3. 分层与依赖

依赖方向严格单向，核心层不 import UI：

```
                    main.py  ──────────────┐
                   /   |    \              │
        cropper_window │  annotator_window │
              │        │        │          │
        viewer_base ───┴────────┘          │
              │                            │
   image_cropper   yolo_annotation          │
              │        │                    │
              └───┬────┴────┬───────────────┘
                  │         │
            yolo_to_json  settings_manager  converter_worker
                  │         │
                  └── lang ─┴── ui_theme
```

- **核心层（无 tkinter）**：`yolo_to_json`、`image_cropper`、`yolo_annotation`、`settings_manager`、`converter_worker`、`lang`、`ui_theme`。可被脚本直接调用（已验证）。
- **视图基类**：`viewer_base.ImageViewerBase`，只负责列表/索引/缩放/平移/坐标换算，鼠标事件通过 `on_draw_start/move/end` 钩子下沉到子类。
- **窗口层**：`main`（主窗口）、`cropper_window`（`CropWindow`）、`annotator_window`（`AnnotatorWindow`），三者都是 `tk.Toplevel`；`main` 持有 `_crop_win` / `_annot_win` 单例引用。
- **共享组件**：`class_manager.ClassManagerFrame`（两处复用）、`ui_theme` 常量、`lang.tr()`。

### 三个入口与生命周期

| 窗口 | 创建者 | 关闭行为 |
|---|---|---|
| 主窗口 | `main.main()` → `YoloToJsonApp()` | `_on_close` 存窗口几何 + 退出 |
| 裁切工具 | 菜单 工具 → `_open_cropper` | `_on_close` 存几何/输出模式 |
| 标注工具 | 菜单 工具 → `_open_annotator` | `_on_close` 存几何 + 未保存检查 |

## 4. 三条主要数据流

### 4.1 转换（YOLO txt → LabelMe JSON）
```
_start_conversion (main:607)
  → _gather_config + _validate
  → ConversionWorker.start()          [后台线程]
      → yolo_to_json.batch_convert_yolo_to_labelme
          为图像目录建一次 (stem+ext).lower() 索引 → 每 txt 查表
          → yolo_to_json.yolo_to_labelme_json → Pillow 取尺寸 → json.dump
  → root.after(100, _tick_worker)     [主线程轮询]
      → 排空 _callback_queue（进度/日志）
      → worker 结束则 _finish_conversion (main:655)
```
关键约定：worker 不碰任何 tkinter 对象，只往 `queue.Queue` 塞回调闭包；取消靠 `cancel_check()` 逐文件检查。

### 4.2 裁切（归一化框 → 逐图裁切）
`Region(x,y,w,h)` 归一化存储，`to_pixels()` 时按目标图尺寸换算，因此同一个框可套用到不同尺寸的图。
批量走 `BatchCropWorker`（cropper_window:205），逻辑在 `image_cropper.batch_crop`。

### 4.3 标注（编辑 → txt）
```
_open_folder (annotator:666)
  → viewer.set_files()  → 打开图像
  → 逐图 parse_yolo_txt 建 _annot_cache: path → boxes   （✓ 标记/筛选/跳转共用）
画框/移动/缩放 → AnnotatorViewer.on_draw_* → Region 列表
  → _begin/_commit_gesture 维护每图独立撤销栈
  → _save (annotator:974) → write_yolo_txt + 类别变更时写 classes.txt
删除 (Shift+D) → _delete_image:831 → _do_delete:859
  → 图像与同名 txt 移动到 图像目录的上一级/_delete
```

## 5. 坐标系约定（改动时最容易出错的地方）

| 空间 | 载体 | 换算 |
|---|---|---|
| 图像像素 | `Region.to_pixels()/from_pixels()` | 归一化 × 图像宽高 |
| 画布像素 | `ViewerBase.image_to_canvas / canvas_to_image` | `ix*_scale+_off_x` |
| 视口缩放 | `_scale`（当前）、`_fit_scale`（适配）、`_user_scale`（None=自动适配） | `zoom_at()` 以光标为锚点 |

`Region.label` 存的是 **class_id 的字符串**（标注模块复用裁切模块的 dataclass 的方式）。

## 6. 配置持久化（`config.ini`，`[Settings]` 段）

| 键 | 读取方 | 说明 |
|---|---|---|
| `last_input_dir` / `last_image_dir` / `last_output_dir` | main | 上次路径 |
| `input_mode` | main | `single` / `batch` |
| `class_names` | main / annotator | JSON：`{"0": "defect"}` |
| `conflict_action` | main / cropper | 规范化为 `overwrite` / `skip`（含旧版中文值兼容） |
| `language` | main | `zh` / `en`，默认 `zh` |
| `window_geometry` | main | tkinter geometry 字符串 |
| `crop_*` | cropper | 输出模式/目录/自动保存/几何 |
| `annot_*` | annotator | 自动保存/几何/上次类别 id |
| `delete_remember` / `delete_default_yes` | annotator | 删除确认「不再询问」 |

写入策略：任何 `set_*` 立即整文件重写（`settings_manager._save:37`）。

## 7. 构建与版本号

版本号需同步 **3 处**（当前一致，均为 1.3.3.0）：`main.py:31` 的 `VERSION`、
`version_info.txt` 的 `filevers/prodvers/FileVersion/ProductVersion`、`README.md` 标题与正文。

`build.spec` 用 `hiddenimports` **手写**列出 12 个模块——新增模块若忘记登记，打包后才会在运行时 ImportError。
打包资源靠 `icon/main_label.png`（`datas`）与 `.ico`（`EXE.icon`）；运行期用 `_resource_path()` 兼容 `sys._MEIPASS`。

## 8. 既有约定

- 源文件 UTF-8；`config.ini` 以 UTF-8 读写（`settings_manager:33/38`）。
- YOLO txt 写入 6 位小数；读取时对 `[0,1]` 越界值做钳制，非法行静默跳过。
- i18n：所有用户可见文案走 `lang.tr(key)`；`tr()` 缺键时**静默返回键名本身**（不报错）。
- 颜色/字体统一在 `ui_theme.py`（个别窗口仍写死颜色，见优化清单）。
- 代码注释与文档使用英文，README/界面文案中文优先。

## 9. 验证基线（接管时的实测结论）

在本机实测通过的项目，可作为后续改动的回归基线：

1. `python -m compileall` 全部 12 模块 → 无语法错误。
2. 隐藏窗口构造真实 GUI：主窗口 / 裁切窗口 / 标注窗口全部创建成功并能干净销毁
   （标题分别为 `YoloToJson — … v1.3.3.0`、`图像裁切工具 — YoloToJson`、`YOLO 标注工具 — YoloToJson`）。
3. 转换链路端到端：640×480 图 + 2 行 txt → JSON 两框，坐标 `[[224,144],[416,144],[416,336],[224,336]]` 正确。
4. 标注读写往返：`parse_yolo_txt → write_yolo_txt` 数值一致（仅格式化位数差异）。
5. 裁切链路：归一化 `(0.1,0.1,0.5,0.5)` → 320×240 输出正确。
6. 疑似「PIL 占用图像文件导致 Shift+D 删除失败」**已排除**：jpg/png/bmp/tif 在图像对象存活时 `shutil.move` 均成功，不存在文件锁。

## 10. 已知结构问题（详见 `docs/OPTIMIZATION_BACKLOG.md`）

- 无任何自动化测试，上一轮验证靠临时脚本，未入库。
- 图像扩展名清单在 3 处各自硬编码（`yolo_to_json:16`、`viewer_base:82`、`image_cropper:149`）。
- 菜单构建代码两份（`main:523` `_setup_menu` 与 `main:563` `_apply_language`）。
- 模态对话框样板在 5 处重复（`transient`/`grab_set`/`resizable`）。
- `annotator_window._build_ui` 115 行、`main._finish_conversion` 60 行，UI 与逻辑混杂。
- 打开的工具窗口不响应语言切换（两个窗口都没有 `_refresh_texts`）。
