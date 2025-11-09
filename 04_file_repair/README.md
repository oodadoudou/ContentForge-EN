============================================================
           Module 4: File Repair & Formatting (04_file_repair)
============================================================

[Overview]
  This module is a “file repair station,” providing tools dedicated to
  fixing and standardizing EPUB and TXT files with common issues such as
  garbled text, layout problems, or missing covers.


[Core Scripts]
  - epub_reformat_and_convert_v2.py (⭐ Comprehensive EPUB tool)
  - cover_repair.py
  - fix_txt_encoding.py
  - txt_reformat.py


[How to Use]
  All features are available from the interactive menu in the project root’s main.py.

  1. In the terminal, go to the ContentForge root and run `python main.py`.
  2. In the main menu, select "4. File Repair & Formatting".
  3. Follow the submenu prompts to choose the function you need.


--------------------- Features and Usage Details ---------------------

+ + + 1. Comprehensive EPUB Repair + + +

  - Script: epub_reformat_and_convert_v2.py
  - Function: Intelligent all-in-one tool. Automatically detects whether an EPUB
    has vertical page progression (rtl) and/or Traditional Chinese content, then
    performs conversions as needed to resolve both in one step.
  - Workflow: After starting, input the directory containing EPUB files. The script
    automatically processes all EPUB files in that directory.


+ + + 2. EPUB Cover Repair + + +

  - Script: cover_repair.py
  - Function: Fixes EPUB cover display issues on some readers (e.g., Kindle) by
    generating a highly compatible standardized cover page.
  - Use case: When the EPUB shows a default icon instead of the actual book cover.
  - Workflow: After starting, input the directory containing EPUB files to repair.


+ + + 3. TXT Encoding Repair (Fix garbled text) + + +

  - Script: fix_txt_encoding.py
  - Function: Automatically fixes garbled text in TXT files caused by encoding problems.
    Tries multiple common encodings (UTF-8, GBK, Big5, etc.) and saves the result in UTF-8.
  - Workflow: After starting, input the directory containing TXT files to repair.


+ + + 4. TXT Paragraph Repair (Fix broken lines) + + +

  - Script: txt_reformat.py
  - Function: Repairs broken lines in novel TXT files (often caused by conversions from PDF).
    Intelligently reconnects split sentences and paragraphs while preserving chapter headings.
  - Workflow: After starting, input the directory containing TXT files to repair.