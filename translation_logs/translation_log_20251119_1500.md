Timestamp: 2025-11-19T15:00:00Z

Scope: shared_assets, shared_utils, tests

Entries:

- File: shared_assets/report_template.html
  - Original: "智能替换报告" → Translated: "Intelligent Replacement Report"
  - Original: "替换规则" → Translated: "Replacement Rules"
  - Original: "点击查看详情" → Translated: "Click to view details"
  - Original: "替换实例" → Translated: "Replacement Instances"
  - Original: "所有替换规则" → Translated: "All Replacement Rules"
  - Original: "报告生成时间" → Translated: "Report generated at"
  - Original: "返回顶部" → Translated: "Back to top"

- File: shared_assets/report_styles.css
  - Original: "/* 返回顶部按钮 */" → Translated: "/* Back to top button */"

- File: shared_assets/report_scripts.js
  - Comments translated to English (Close rules list, Scroll to group, Auto expand, Add highlight, Back-to-top functionality, Listen to scroll, Click back to top, Click backdrop to close, ESC closes modal, Initialize back-to-top).

- File: shared_assets/new_style.css
  - Multiple comments translated (e.g., "首行缩进" → "First-line indent", section headers, TOC notes). Code unchanged.

- File: shared_assets/rules.txt
  - Header and example descriptions translated. Regex examples preserved.
  - Original: "规则文件模板" → "Rules file template"
  - Original: "示例" → "Example"

- File: shared_utils/utils.py
  - Comments, docstrings, and messages translated to English.
  - Original: "全局路径与配置" → "Global Paths & Configuration"
  - Original: "清空终端屏幕" → "Clear the terminal screen"
  - Original: "正在执行" → "Executing"
  - Original: "工作目录" → "Working directory"
  - Original: error messages translated.

- File: shared_utils/epub_style_selector.py
  - Docstring and UI messages translated.
  - STYLE_OPTIONS names, descriptions, features translated to English.

- File: tests/test_main_dispatcher.py
  - Comments and printed messages translated.
  - Menu description strings translated to English; script path logic unchanged.

- File: shared_assets/epub_styles_preview.html
  - Title, headers, section labels translated.
  - Original: "EPUB 样式预览" → "EPUB Style Preview"
  - Original section labels (e.g., "经典简约样式") → "Classic Minimal Style"
  - Common comments translated.

- Files: shared_assets/epub_css/Moonreader/*
  - Header and common section comments translated (e.g., "图片样式" → "Image styles"). CSS rules unchanged.

- File: shared_assets/epub_css/basic/epub_style_classic.css
  - Original: "经典简约样式 - 适合长篇小说" → "Classic minimal style - suitable for long novels"
  - Original: "首行缩进" → "First-line indent"

- File: shared_assets/epub_css/basic/epub_style_clean.css
  - Original: "纯净极简样式 - 温和视觉体验" → "Pure minimal style - gentle visual experience"

Verification:
- Compiled Python files successfully via `python -m py_compile` for modified modules (shared_utils and tests unaffected in runtime).
- HTML/CSS/JS formatting preserved; only text and comments changed.
- No functionality changes introduced; only translations applied.