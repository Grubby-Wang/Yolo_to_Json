# 优化工作清单（接管基线 v1.3.3.0）

> 每条都附证据；标注 **已实测** 的结论可以直接采信，标注 **待验证** 的需要动手确认。
> 行号对应 `master_cr` 的 `d388649`。优先级：P0 影响可用性/会崩 → P1 结构债（影响后续开发速度）→ P2 性能 → P3 细节。

## 一、P0 已确认缺陷（3 条，均可复现）

### P0-1 中文界面下转换完成后抛 KeyError，收尾流程被中断
- **证据**：`main.py:692` 调用 `lang.tr('log_complete', success=…, failed=…, skipped=…)`，
  而 `lang.py:151` 的中文串含 `{total}` 占位符，调用未传 `total`。
  实测：`lang.tr('log_complete', success=1, failed=0, skipped=0)` → `KeyError: 'total'`（仅中文；英文串无 `{total}`，故英文界面不触发）。
  **端到端复现**（构造真实 `YoloToJsonApp`、语言=中文、喂入一个成功的转换结果后调用 `_finish_conversion()`）：
  `RESULT: raised KeyError -> 'total'`，且配置文件未被 `_save_settings()` 重写 —— 与下面的后果描述完全吻合。
- **后果**：`_finish_conversion`（`main.py:655`）在 693 行抛出，其后的
  `self._worker = None`、`self._save_settings()` 全部跳过；日志里没有「转换完成…」摘要，
  有错误时的完成弹窗也不出现。异常被 tkinter 回调机制吞掉（无控制台 exe 中完全静默），所以一直没被发现。
- **修复**：`lang.tr('log_complete', …, total=r.get('total', 0))`；顺手把英文串补上 `{total}`，让两种语言信息量一致。
- **防御性加固**：`lang.tr` 目前用 `val.format(**kwargs)`，占位符缺失直接抛异常。
  建议改为「缺参数时保留占位符原样」并记录一次告警，避免同类问题再次炸掉主流程。
- **验收**：中文界面跑一次批量转换，日志出现「转换完成。成功 N，失败 0，跳过 0（共 M）。」，
  且转换后 `config.ini` 的 mtime 更新；补一条断言 `total` 必传的单测。

### P0-2 旧版 `config.ini`（GBK 编码）会导致程序启动即崩
- **证据**：`settings_manager.py:33` 直接 `self._cfg.read(ini_path, encoding='utf-8')`，无异常处理。
  实测：写一个 GBK 编码的 `config.ini` 后构造 `SettingsManager()` →
  `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb8`。
- **为什么不是理论风险**：仓库自带的 `config.ini` 里已经出现 `conflict_action = 瑕嗙洊`（"覆盖" 被按 GBK 解码）、
  `2026-05-06-鐪熷附婕忔` 这类乱码——说明历史上确实存在「UTF-8 文件被按本地编码读」的时期。
  任何从旧版本升级的机器都可能留着这种文件。
- **修复**：读取时按 `utf-8 → utf-8-sig → gbk` 依次尝试；命中非 UTF-8 时先备份
  `config.ini.bak_<时间戳>`，再用 UTF-8 重写一次，之后正常启动。
- **验收**：分别用 GBK / UTF-8-BOM / 正常 UTF-8 三种 `config.ini` 启动程序，均能进入主窗口，且中文类别名不乱码。**建议同时补单测**（纯逻辑，不需要 GUI）。

### P0-3 切换语言时，已打开的工具窗口不刷新
- **证据**：`main._apply_language`（`main.py:563`）只刷新主窗口的 5 个面板；
  `cropper_window.py` / `annotator_window.py` 中检索 `_refresh_texts`/`_apply_language` = **0 处**。
- **后果**：开着裁切/标注窗口时切中英文，主窗口变了、工具窗口仍是旧语言，直到关掉重开。
- **修复**：两个窗口各加 `_refresh_texts()`（收集已有控件的 `configure(text=…)`），
  由 `main._apply_language` 在窗口存在时调用；同时重置那两个「本地化文本 ↔ 内部 key」的筛选下拉框取值。
- **验收**：打开标注窗口 → 切英文 → 按钮/面板标题/筛选下拉框全部变英文，且筛选逻辑仍按内部 key 生效。

## 二、P1 结构债务（影响下一步开发效率）

### P1-1 仓库内 0 个自动化测试 —— 建议第一件事就补
上一轮（zcode）的验证全靠临时目录脚本，不落库，所以每次改动都要手工回归三个窗口。
核心层（`yolo_to_json` / `yolo_annotation` / `image_cropper` / `settings_manager`）**不依赖 tkinter**，
天然可测；GUI 层可用「隐藏窗口构造 + 销毁」做冒烟（我已验证该手法可行）。
- **建议**：新增 `tests/`，pytest 覆盖：转换端到端、YOLO 读写往返与越界钳制、`Region` 像素/归一化往返、
  config 编码兼容、i18n 占位符一致性（自动比对 `STRINGS` 的中英占位符集合）、GUI 构造冒烟。
- **配套**：`requirements-dev.txt`（pytest）；README 补一节「运行测试」。
- **验收**：`python -m pytest -q` 全绿，且能覆盖 P0-1/P0-2 两条回归。

### P1-2 图像扩展名清单硬编码 3 份
`yolo_to_json.py:16`（`DEFAULT_IMAGE_EXTENSIONS`）、`viewer_base.py:82`、`image_cropper.py:149`。
新增格式（如 `.webp`）要改 3 处，漏改会出现「列表能看见但转换找不到图」这类不一致。
**改法**：只保留 `yolo_to_json.DEFAULT_IMAGE_EXTENSIONS` 为唯一来源，另两处改为 import 默认值。

### P1-3 菜单构建代码两份
`main._setup_menu`（`main.py:523`，33 行）先建空菜单，随后 `_apply_language`（`main.py:563`，44 行）
用同样的结构再建一遍。两份必须手工同步，加一个菜单项要改两处。
**改法**：抽 `_build_menu()` 统一「删空 → 按当前语言重建」，`_setup_menu` 只调它一次。

### P1-4 模态对话框样板重复 5 处
`annotator_window.py:394-396`、`annotator_window.py:645-646`、`cropper_window.py:122-124`、`cropper_window.py:161-162`
各自重复 `resizable(False, False)` + `transient(parent)` + `grab_set()`，另有两处 `focus_force()`。
**改法**：`ui_theme.py` 旁新增 `ui_dialogs.py`，提供 `ModalDialog(tk.Toplevel)` 基类（居中、模态、Esc 取消、返回值语义）。

### P1-5 巨型方法：UI 与业务逻辑混在一个函数里
| 位置 | 长度 | 问题 |
|---|---|---|
| `annotator_window.AnnotatorWindow._build_ui` | `annotator:447`，**115 行** | 顶部两条工具栏、画布、右侧框列表、图像列表、筛选条、状态栏全在一个函数里；改一处布局要通读全函数 |
| `main.YoloToJsonApp._finish_conversion` | `main:655`，**60 行** | 收尾 + 日志 + 弹窗 + 状态栏 + 清理混写，P0-1 正是这里的脆弱点 |
| `cropper_window.CropWindow._build_ui` | `cropper:260`，83 行 | 同上 |
| `class_manager.ClassManagerFrame.__init__` | `class_manager:24`，46 行 | 控件创建与配置读取耦合 |
**改法**（渐进，不必大动）：按「条/面板」拆成 `_build_top_bar` / `_build_body` / `_build_side_panels` 等私有方法，行为不变，纯搬代码。

### P1-6 键位绑定窗口与画布各绑一遍，必须手工同步
`annotator_window._bind_keys`（`annotator:562`，32 行）对 `a/A/d/D/←/→/Esc/Delete/Ctrl+Shift+A/D`
既绑 `self.bind(...)` 又绑 `self._viewer.canvas.bind(...)`，共约 20 条。新增快捷键漏绑一处就会出现
「焦点在画布上时快捷键失灵」。
**改法**：改为「序列 → 处理器」的字典，一次循环同时绑两个目标。

### P1-7 三个窗口之间重复的小工具函数
`_tick_worker`（`main:640` 与 `cropper_window:516`）、`_persist_auto_save`（`annotator:1013`、`cropper:564`）、
`_refocus`（`annotator:691`、`cropper:375`）、`_open_folder`（`annotator:666`、`cropper:353`）。
**改法**：抽出 `worker_bridge.py`（队列轮询）或直接在 `viewer_base` 旁放一个 `WindowMixin`。

### P1-8 `remove_path` 用精确字符串匹配查找下标（潜在）
`viewer_base.py:142` `self._files.index(path)`：Windows 路径大小写不敏感，若调用方传入大小写/规范化形式不同的路径，
会静默返回旧下标、不删除。当前 `_do_delete` 传的是 `current_path` 原串，所以暂未触发。
**改法**：改用 `os.path.normcase` 归一化的映射表（或 `_path_index` 字典）维护下标。

### P1-9 文档与仓库结构不一致
`README.md:155` 的「项目结构」树缺 `icon/`（打包资源，缺它 exe 没图标）与本次新增的 `docs/`；
`.zcode/plans/` 里的上一轮计划被 `.gitignore` 忽略，随目录清理即丢失。
**已处理**：`docs/` 已建立并纳入；上一轮计划归档到 `docs/history/`；`README.md` 的结构树已补上 `icon/` 与 `docs/`。

## 三、P2 性能（已量化，最大的一项是 P2-1）

### P2-1 拖动/缩放框时每帧重建整张位图 —— 大图明显掉帧
- **证据**：`viewer_base._render`（`viewer_base.py:255`）先 `canvas.delete("all")`，再
  `self._pil.resize(...)` + `ImageTk.PhotoImage(...)` 重建显示位图；而 `on_draw_move`
  （`annotator:238`）**每个鼠标移动事件**都调用 `self._render()`（`annotator:259`）。
- **实测成本**（本机 Pillow 12.2，画布 1600×1000）：

  | 原图 | 显示尺寸 | 单次重绘 | 帧率上限 |
  |---|---|---|---|
  | 1280×960 | 1333×1000 | **8.7 ms** | ~115 fps |
  | 4000×3000 | 1333×1000 | **57.7 ms** | ~17 fps |
  | 6000×4000 | 1500×1000 | **86.9 ms** | ~12 fps |

  也就是说 12 MP 的照片在拖动框时只有十几帧，手感明显发滞；每帧还要重建全部框的图元。
- **改法**（收益最高、风险可控）：
  1. `viewer_base` 缓存 `PhotoImage`，仅在「换图 / 缩放比例变化 / 视口偏移变化」时重建位图；
  2. 新增 `_render_overlay_only()`：`delete("overlay")` 后只重画框与手柄；
  3. `on_draw_move` 改调 overlay-only；`_render()` 留给换图与缩放。
- **验收**：拖动 12 MP 图片的框时帧率跟随鼠标（主观流畅），且框位置、手柄、拖拽虚框与改动前一致。

### P2-2 打开文件夹时在 UI 线程里逐张解析 txt
`_refresh_img_list`（`annotator:792`）对每个可见行调用 `_annot_for(p)`（`annotator:761`）→ `parse_yolo_txt`。
`_annot_cache` 是惰性的，所以**第一次刷新会把整个文件夹的 txt 全读一遍**，发生在主线程；
且 `_refresh_img_list` 在换图（`annotator:890`）、框变化（`annotator:902`）、保存（`annotator:985`）时都会被调用，
每次都 `delete` 全部行再全量 `insert`。
- **后果**：几千张图的文件夹，打开瞬间卡住；之后每按一次 A/D 都重建几千行 Treeview。
- **改法**：打开文件夹时一次性后台扫描（线程 + 进度），列表改为「仅在筛选变化时重建」，
  当前图高亮只做 `selection_set` + `see`；单行 ✓ 状态用 `item(iid, values=…)` 就地更新。
- **验收**：5000 张图文件夹打开后 UI 不冻结；A/D 连按不重排列表。

### P2-3 每次设置变更都整文件重写 `config.ini`
`settings_manager._save`（`settings_manager.py:37`）在每次 `set_*` 时被调用；勾选自动保存、
改窗口大小、切类别都会立刻落盘。本地 SSD 无感，网络盘/机械盘会有卡顿。
**改法**：内存置脏标记 + `after(500ms)` 去抖，或仅在窗口关闭/转换结束时统一写。

## 四、P3 细节（顺手清理，工作量小）

1. `lang.tr` 缺键时静默返回键名（`lang.py:47`）→ 开发期应 `warnings.warn`，避免把 key 露给用户。
2. `log_complete` 中文/英文占位符不一致（`lang.py:151`）——英文丢了「共 M 个」的信息，随 P0-1 一起修。
3. 7 个 i18n 键疑似未被字面引用：实测其中 `crop_done`、`crop_status_progress`、`file_not_found`、
   `log_done_summary`、`select_yolo_file` 均无实际调用点（仅 `lang.py` 定义），可清理；
   `log_skipped` 通过 `_FILE_STATUS_LOG` 字典间接使用，**不能删**。
4. 颜色绕过主题：`annotator_window.py:439` 写死 `bg="#F0F2F5"`、`:490` 写死 `#6B7280`、`:346` 写死 `#888888`，
   与 `ui_theme.py` 中同名常量重复。
5. `yolo_to_json.py:49` `open(yolo_file_path, 'r')` 未指定编码（标注模块已按 utf-8→gbk 兜底，转换器没有）。
6. `yolo_to_json.py:202`：未传 `log_callback` 时把**成功信息**也塞进 `result['errors']`，字段语义被污染。
7. `viewer_base.py:125` `Image.open` 未 `close()`；已实测不会锁文件（删除/移动无影响），但异常图片会留悬挂句柄。
8. `annotator_window.py:299-304` 拖拽误触分支同时用 `_cancel_gesture()` 又手工 `self.boxes = orig` 回滚，两条回滚路径重叠，建议只留一条。

## 五、建议的推进顺序

| 阶段 | 内容 | 产出 | 风险 |
|---|---|---|---|
| **1. 稳住**（1 次会话） | P0-1 / P0-2 / P0-3 + P1-1 测试骨架 | 3 个可复现缺陷关闭，`pytest` 首次全绿 | 低，改动集中在 `lang/main/settings_manager` |
| **2. 提速**（1 次会话） | P2-1 位图缓存 + overlay-only 重绘 | 大图拖框流畅，可量化对比 | 中，需回归三个窗口的缩放/平移/拖拽 |
| **3. 还债** | P1-2/3/4/6/7 小重构 + P2-2 列表增量刷新 | 新增格式/菜单/快捷键只改一处 | 中，纯结构调整，行为不变 |
| **4. 加功能** | 待定（见下） | — | — |

**第 4 阶段的功能候选项**（需你确认优先级）：
- 标注器：框复制/粘贴、键盘微调（方向键 ±1px）、跨图查找同类别、导出 LabelMe JSON（反向转换，目前只做 txt→json）。
- 转换器：支持分割标注（多边形）→ LabelMe `polygon`；支持 YOLO-seg。
- 裁切器：预设裁切比例、按类别裁切。
