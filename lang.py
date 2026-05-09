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
}
