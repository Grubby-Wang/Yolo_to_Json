"""
Internationalization (i18n) module for YoloToJson.

Supports Chinese (zh) and English (en). Default: Chinese.
"""


# ── Available languages ──

LANGS = {
    'zh': '中文',
    'en': 'English',
}

_current = 'zh'
_listeners = []  # callbacks invoked after set_language()


def get_current():
    return _current


def set_language(code):
    global _current
    if code not in LANGS:
        return
    _current = code
    for cb in _listeners:
        try:
            cb(code)
        except Exception:
            pass


def on_language_change(callback):
    """Register a callback(code) to be called when language changes."""
    _listeners.append(callback)


def tr(key, *args, **kwargs):
    """Return the translated string for the given key in the current language.

    Supports Python format-style interpolation: tr('found_files', n=5)
    """
    val = STRINGS.get(key, {}).get(_current)
    if val is None:
        val = STRINGS.get(key, {}).get('en', key)
    if args or kwargs:
        return val.format(*args, **kwargs)
    return val


# ── All translatable strings ──

STRINGS = {
    # ── Window / App ──
    'app_title': {
        'zh': 'YoloToJson — YOLO标注转LabelMe JSON转换器',
        'en': 'YoloToJson — YOLO to LabelMe JSON Converter',
    },

    # ── Menu ──
    'menu_file':     {'zh': '文件', 'en': 'File'},
    'menu_view':     {'zh': '查看', 'en': 'View'},
    'menu_language': {'zh': '语言', 'en': 'Language'},
    'menu_help':     {'zh': '帮助', 'en': 'Help'},
    'lang_zh':       {'zh': '中文', 'en': '中文'},
    'lang_en':       {'zh': 'English', 'en': 'English'},
    'menu_clear_log': {'zh': '清除日志', 'en': 'Clear Log'},
    'menu_exit':      {'zh': '退出', 'en': 'Exit'},
    'menu_about':     {'zh': '关于', 'en': 'About'},

    # ── About dialog ──
    'about_title': {'zh': '关于 YoloToJson', 'en': 'About YoloToJson'},
    'about_text': {
        'zh': ('YoloToJson v{version}\n\n'
               '将YOLO格式标注文件转换为LabelMe JSON格式。\n'
               '支持单文件和批量文件夹转换。\n\n'
               '基于 Python / tkinter 构建。'),
        'en': ('YoloToJson v{version}\n\n'
               'Convert YOLO format annotation files to LabelMe JSON format.\n'
               'Supports both single-file and batch folder conversion.\n\n'
               'Built with Python / tkinter.'),
    },

    # ── File Input Panel ──
    'input_config':    {'zh': '输入配置', 'en': 'Input Configuration'},
    'input_mode':      {'zh': '模式:', 'en': 'Mode:'},
    'mode_single':     {'zh': '单个文件', 'en': 'Single File'},
    'mode_batch':      {'zh': '批量文件夹', 'en': 'Batch Folder'},
    'yolo_source':     {'zh': 'YOLO .txt 源文件:', 'en': 'YOLO .txt Source:'},
    'browse':          {'zh': '浏览...', 'en': 'Browse...'},
    'image_dir':       {'zh': '图像文件夹:', 'en': 'Image Directory:'},
    'select_yolo_file': {'zh': '选择YOLO .txt文件', 'en': 'Select YOLO .txt File'},
    'select_yolo_folder': {'zh': '选择包含YOLO .txt文件的文件夹', 'en': 'Select Folder with YOLO .txt Files'},
    'select_image_folder': {'zh': '选择图像文件夹', 'en': 'Select Image Directory'},
    'yolo_file_filter': {'zh': 'YOLO文件 (*.txt)', 'en': 'YOLO Files (*.txt)'},
    'all_files':       {'zh': '所有文件 (*.*)', 'en': 'All Files (*.*)'},

    # ── Class Manager Panel ──
    'class_mapping':   {'zh': '类别名称映射', 'en': 'Class Name Mapping'},
    'class_add':       {'zh': '添加', 'en': 'Add'},
    'class_remove':    {'zh': '删除', 'en': 'Remove'},
    'class_import_csv': {'zh': '导入CSV', 'en': 'Import CSV'},
    'class_export_csv': {'zh': '导出CSV', 'en': 'Export CSV'},
    'class_col_id':    {'zh': '类别ID', 'en': 'Class ID'},
    'class_col_name':  {'zh': '类别名称', 'en': 'Class Name'},
    'class_count':     {'zh': '{n} 个类别', 'en': '{n} classes'},
    'class_default_name': {'zh': '类别_{n}', 'en': 'class_{n}'},

    # ── Output Panel ──
    'output_config':   {'zh': '输出配置', 'en': 'Output Configuration'},
    'output_dir':      {'zh': '输出文件夹:', 'en': 'Output Directory:'},
    'select_output_folder': {'zh': '选择输出文件夹', 'en': 'Select Output Directory'},
    'if_file_exists':  {'zh': '若文件已存在:', 'en': 'If file exists:'},
    'conflict_overwrite': {'zh': '覆盖', 'en': 'Overwrite'},
    'conflict_skip':   {'zh': '跳过', 'en': 'Skip'},

    # ── Conversion Panel ──
    'conversion':      {'zh': '转换', 'en': 'Conversion'},
    'btn_convert':     {'zh': '开始转换', 'en': 'Start Conversion'},
    'btn_cancel':      {'zh': '取消', 'en': 'Cancel'},
    'btn_open_output': {'zh': '打开输出目录', 'en': 'Open Output Folder'},
    'status_ready':    {'zh': '就绪', 'en': 'Ready'},
    'status_converting': {'zh': '转换中...', 'en': 'Converting...'},
    'status_converting_n': {'zh': '正在转换 {current}/{total}...', 'en': 'Converting {current}/{total}...'},
    'status_completed': {'zh': '已完成: {success}/{total} 成功', 'en': 'Completed: {success}/{total} succeeded'},

    # ── Log Panel ──
    'log_panel':       {'zh': '转换日志', 'en': 'Conversion Log'},
    'log_clear':       {'zh': '清除', 'en': 'Clear'},
    'log_save':        {'zh': '保存日志...', 'en': 'Save Log...'},
    'log_save_dialog': {'zh': '日志文件 (*.log)', 'en': 'Log Files (*.log)'},
    'log_txt_filter':  {'zh': '文本文件 (*.txt)', 'en': 'Text Files (*.txt)'},

    # ── Status Bar ──
    'statusbar_ready': {'zh': '就绪', 'en': 'Ready'},
    'statusbar_converting': {'zh': '转换中...', 'en': 'Converting...'},
    'statusbar_canceling': {'zh': '正在取消...', 'en': 'Canceling...'},
    'statusbar_error': {'zh': '发生错误', 'en': 'Error occurred'},
    'statusbar_done':  {'zh': '完成: {success}/{total} 成功', 'en': 'Done: {success}/{total} succeeded'},

    # ── Log messages ──
    'log_started':     {'zh': 'YoloToJson 已启动，等待转换操作。', 'en': 'YoloToJson started. Ready for conversion.'},
    'log_starting_convert': {'zh': '开始转换...', 'en': 'Starting conversion...'},
    'log_found_files': {'zh': '找到 {n} 个YOLO文件，开始转换...', 'en': 'Found {n} YOLO file(s), starting conversion...'},
    'log_converted':   {'zh': '已转换 {base}.txt → {base}.json', 'en': 'Converted {base}.txt → {base}.json'},
    'log_failed':      {'zh': '转换失败: {base}.txt', 'en': 'Failed to convert {base}.txt'},
    'log_skipped':     {'zh': '跳过 {base}.txt — 未找到匹配的图像', 'en': 'Skipped {base}.txt — no matching image found'},
    'log_skip_exists': {'zh': '跳过 {base}.txt — 输出文件已存在', 'en': 'Skipped {base}.txt — output already exists'},
    'log_complete':    {'zh': '转换完成。成功 {success}，失败 {failed}，跳过 {skipped}（共 {total}）。', 'en': 'Conversion complete. {success} succeeded, {failed} failed, {skipped} skipped.'},
    'log_cancel_req':  {'zh': '已请求取消...', 'en': 'Cancellation requested...'},
    'log_no_txt':      {'zh': '在 {path} 中未找到 .txt 文件', 'en': 'No .txt files found in {path}'},
    'log_input_missing': {'zh': '输入文件夹不存在: {path}', 'en': 'Input folder does not exist: {path}'},
    'log_done_summary':  {'zh': '完成。成功 {success}，失败 {failed}，跳过 {skipped}（共 {total} 个文件）', 'en': 'Done. {success} success, {failed} failed, {skipped} skipped (of {total} total)'},

    # ── Validation ──
    'val_select_file_or_folder': {'zh': '请选择YOLO .txt文件或文件夹。', 'en': 'Please select a YOLO .txt file or folder.'},
    'val_input_not_exist': {'zh': '输入路径不存在: {path}', 'en': 'Input path does not exist: {path}'},
    'val_specify_output': {'zh': '请指定输出文件夹。', 'en': 'Please specify an output directory.'},
    'val_specify_image': {'zh': '请指定图像文件夹。', 'en': 'Please specify the image directory.'},
    'val_image_not_exist': {'zh': '图像文件夹不存在: {path}', 'en': 'Image directory does not exist: {path}'},
    'val_define_class': {'zh': '请至少定义一个类别名称。', 'en': 'Please define at least one class name.'},
    'val_title':       {'zh': '输入验证错误', 'en': 'Validation Error'},
    'error_title':     {'zh': '转换错误', 'en': 'Conversion Error'},
    'complete_title':  {'zh': '转换完成', 'en': 'Conversion Complete'},
    'complete_msg':    {'zh': '成功: {success}\n失败: {failed}\n跳过: {skipped}\n\n{nerr} 个错误 — 请查看日志了解详情。', 'en': 'Succeeded: {success}\nFailed: {failed}\nSkipped: {skipped}\n\n{nerr} error(s) — check the log for details.'},
    'import_error':    {'zh': '导入失败', 'en': 'Import Error'},
    'import_failed_msg': {'zh': '导入CSV失败:\n{e}', 'en': 'Failed to import CSV:\n{e}'},
    'export_error':    {'zh': '导出失败', 'en': 'Export Error'},
    'export_failed_msg': {'zh': '导出CSV失败:\n{e}', 'en': 'Failed to export CSV:\n{e}'},
    'no_input_path':   {'zh': '未指定输入路径。', 'en': 'No input path specified.'},
    'no_output_path':  {'zh': '未指定输出文件夹。', 'en': 'No output directory specified.'},
    'no_match_image':  {'zh': '未找到与 {base}.txt 匹配的图像文件', 'en': 'No matching image found for {base}.txt'},
    'file_not_found':  {'zh': '文件未找到: {path}', 'en': 'File not found: {path}'},

    # ── CSV dialogs ──
    'csv_filter':      {'zh': 'CSV文件 (*.csv)', 'en': 'CSV Files (*.csv)'},

    # ── Default classes & classes.txt ──
    'class_gen_count': {'zh': '类别数量:', 'en': 'Count:'},
    'class_gen':       {'zh': '生成默认类别', 'en': 'Generate Defaults'},
    'class_gen_title': {'zh': '生成默认类别', 'en': 'Generate Default Classes'},
    'class_gen_confirm': {
        'zh': '将清除现有映射并生成 {n} 个默认类别（类别_0 ~ 类别_{n1}），\n可直接使用默认名称，也可双击名称列修改。是否继续？',
        'en': 'Replace existing mapping with {n} default classes (class_0 ~ class_{n1})?\nYou can keep the default names or double-click a name to edit it.'},
    'class_import_txt': {'zh': '导入classes.txt', 'en': 'Import classes.txt'},
    'class_export_txt': {'zh': '导出classes.txt', 'en': 'Export classes.txt'},
    'classes_txt_filter': {'zh': 'classes.txt 类别文件 (*.txt)', 'en': 'classes.txt (*.txt)'},
    'classes_replace_confirm': {
        'zh': '导入将替换现有类别映射（共 {n} 个类别），是否继续？',
        'en': 'Import will replace the existing class mapping ({n} classes). Continue?'},
    'classes_txt_empty': {'zh': '文件中未找到任何类别名称。', 'en': 'No class names found in the file.'},
    'import_dup_skipped': {'zh': '导入完成，{n} 行因类别ID无效或重复被跳过。', 'en': 'Imported. {n} row(s) skipped (invalid or duplicate class ID).'},
    'import_no_rows':   {'zh': '文件中没有有效行（需要 类别ID,类别名称）。', 'en': 'No valid rows found (expected: class_id,class_name).'},

    # ── Cancellation ──
    'status_canceled':  {'zh': '已取消（成功 {success}/{total}）', 'en': 'Canceled ({success}/{total} succeeded)'},
    'statusbar_canceled': {'zh': '已取消: {success}/{total} 成功', 'en': 'Canceled: {success}/{total} succeeded'},
    'log_canceled':     {'zh': '转换已取消 — 成功 {success}，失败 {failed}，跳过 {skipped}（已处理 {done}/{total}）。',
                         'en': 'Conversion canceled — {success} succeeded, {failed} failed, {skipped} skipped ({done}/{total} processed).'},

    # ── Image viewer / crop tool ──
    'viewer_empty_hint': {'zh': '打开图像文件夹以浏览', 'en': 'Open an image folder to browse'},
    'menu_tools':       {'zh': '工具', 'en': 'Tools'},
    'menu_crop_tool':   {'zh': '图像裁切工具...', 'en': 'Image Cropping Tool...'},
    'crop_tool':        {'zh': '图像裁切工具', 'en': 'Image Cropping Tool'},
    'crop_open_folder': {'zh': '打开图像文件夹', 'en': 'Open Image Folder'},
    'crop_open_files':  {'zh': '打开图像', 'en': 'Open Image(s)'},
    'crop_prev':        {'zh': '上一张', 'en': 'Prev'},
    'crop_next':        {'zh': '下一张', 'en': 'Next'},
    'crop_goto':        {'zh': '跳转:', 'en': 'Go to:'},
    'crop_auto_save':   {'zh': '默认保存（免确认）', 'en': 'Auto-save (no confirm)'},
    'crop_out_source':  {'zh': '原图所在文件夹', 'en': 'Same folder as image'},
    'crop_out_custom':  {'zh': '指定目录:', 'en': 'Custom dir:'},
    'crop_btn_apply_all': {'zh': '应用到所有图像', 'en': 'Apply to All Images'},
    'crop_btn_apply_sel': {'zh': '应用到选中图像...', 'en': 'Apply to Selected...'},
    'crop_rect_lbl':    {'zh': '裁切框:', 'en': 'Crop rect:'},
    'crop_rect_none':   {'zh': '未绘制', 'en': 'none'},
    'crop_status_save': {'zh': '已保存: {path}', 'en': 'Saved: {path}'},
    'crop_status_progress': {'zh': '正在批量裁切 {current}/{total}...', 'en': 'Batch cropping {current}/{total}...'},
    'crop_batch_start': {'zh': '开始批量裁切 {n} 张 → {path}', 'en': 'Batch cropping {n} image(s) → {path}'},
    'crop_dir_source':  {'zh': '原图所在文件夹', 'en': 'source folders'},
    'crop_done':        {'zh': '已裁切: {base}', 'en': 'Cropped: {base}'},
    'crop_failed':      {'zh': '裁切失败: {base}', 'en': 'Crop failed: {base}'},
    'crop_skip_exists': {'zh': '跳过（已存在）: {base}', 'en': 'Skipped (exists): {base}'},
    'crop_batch_done':  {'zh': '批量裁切完成。成功 {success}，失败 {failed}，跳过 {skipped}（共 {total}）。',
                         'en': 'Batch crop complete. {success} succeeded, {failed} failed, {skipped} skipped (of {total}).'},
    'crop_batch_canceled': {'zh': '批量裁切已取消 — 成功 {success}，失败 {failed}，跳过 {skipped}（已处理 {done}/{total}）。',
                            'en': 'Batch crop canceled — {success} succeeded, {failed} failed, {skipped} skipped ({done}/{total} processed).'},
    'crop_confirm_title': {'zh': '保存裁切图像', 'en': 'Save Cropped Image'},
    'crop_confirm_msg': {'zh': '保存裁切图像到:\n{path}\n\n尺寸: {w} × {h} px', 'en': 'Save cropped image to:\n{path}\n\nSize: {w} × {h} px'},
    'crop_confirm_btn_save':   {'zh': '保存', 'en': 'Save'},
    'crop_confirm_btn_other':  {'zh': '更改文件夹...', 'en': 'Change Folder...'},
    'crop_confirm_btn_cancel': {'zh': '取消', 'en': 'Cancel'},
    'crop_no_rect':     {'zh': '请先在图像上拖拽绘制裁切框。', 'en': 'Draw a crop rectangle on the image first.'},
    'crop_no_image':    {'zh': '请先打开图像。', 'en': 'Open an image first.'},
    'crop_select_title': {'zh': '选择要应用的图像', 'en': 'Select Images to Apply'},
    'crop_select_all':  {'zh': '全选', 'en': 'Select All'},
    'crop_select_none': {'zh': '全不选', 'en': 'Select None'},
    'crop_select_invert': {'zh': '反选', 'en': 'Invert'},
    'crop_select_ok':   {'zh': '应用', 'en': 'Apply'},
    'crop_select_col':  {'zh': '图像', 'en': 'Image'},
    'crop_batch_confirm': {'zh': '将把当前裁切框应用到 {n} 张图像并保存，是否继续？',
                           'en': 'Apply the current crop rectangle to {n} image(s) and save?'},
    'crop_batch_title': {'zh': '批量裁切', 'en': 'Batch Crop'},
    'crop_error_title': {'zh': '裁切错误', 'en': 'Crop Error'},
    'crop_log':         {'zh': '裁切日志', 'en': 'Crop Log'},
    'image_filter':     {'zh': '图像文件 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)', 'en': 'Image Files (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)'},
    'select_folder_title': {'zh': '选择图像文件夹', 'en': 'Select Image Folder'},
}
