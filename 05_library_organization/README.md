============================================================
           Module Five: Library Organization (05_library_organization)
============================================================

[Overview]
This module provides a set of powerful automation tools to organize, translate,
rename, and archive your local files and folders, turning a cluttered downloads
directory into a tidy library.

[Core Scripts]

translate_and_org_dirs.py (⭐ Core organization pipeline)

folder_codec.py (⭐ File/Folder encryption tool)

extract_epub_css.py

[Usage]
All features of this module are integrated into the interactive menu in the project root's main.py.

In the terminal, navigate to the ContentForge root directory and run: python main.py

Choose "5. Library Organization" from the main menu.

Follow the submenu prompts to select the feature you need.

--------------------- Features & Usage Details ---------------------

Smart Organization and Folder Translation + + +

<!-- end list -->

  - **Script**: `translate_and_org_dirs.py`
  - **Purpose**: A powerful fully automated pipeline for organizing and translation, suitable for handling the entire process from download to final archiving.
  - **Core Flow**:
    1.  **File Preprocessing**: Automatically groups loose files (such as pdf, epub, jpg, zip, etc.) in the root directory based on filenames and moves them into newly created subfolders.
    2.  **AI Translation**: Calls an AI API to translate folder names from Korean or Japanese to fluent Simplified Chinese.
    3.  **Chinese Renaming**: Renames folders according to translation results.
    4.  **Add Pinyin Prefix**: Adds a pinyin first-letter prefix for all Chinese-named folders (e.g., “一部漫画” -> “Y-一部漫画”) to aid sorting.
  - **Operation**: When running this feature, the program will guide you through AI configuration (on first use). After confirmation, simply input the root directory path to organize.

(Tool) Folder Encryption and Decryption + + +

<!-- end list -->

  - **Script**: `folder_codec.py`
  - **Purpose**: Provides a robust two-layer encryption packing and recovery tool. It can process single files or entire folders, producing a `.z删ip` file that is not directly recognizable.
  - **Use Cases**: Useful when you need to securely back up, archive, or share files without allowing direct preview of content or format.
  - **Key Techniques**:
      - **Smart Hybrid Mode**: Automatically detects whether native commands like `7z` and `zip` are installed. If detected, runs in **high-speed mode**; otherwise, switches to a pure Python **compatibility mode**, ensuring it works out-of-the-box on any system (especially Windows).
      - **Preserve Source Files**: The encryption packing process does not delete your original files or folders, ensuring data safety.
      - **Auto Structure Fix**: During decryption, automatically fixes redundant nested directories caused by compression (e.g., `MyFolder/MyFolder/...`).
      - **Helpful Tips**: When running in compatibility mode, at the end the program provides OS-specific install commands (macOS/Windows/Linux) to help you install native tools for future speed improvements.
  - **Operation**: Choose this item in the menu, then select "Encrypt & Pack" or "Decrypt & Restore", and specify the working directory.

(Tool) Extract CSS from EPUB + + +

<!-- end list -->

  - **Script**: `extract_epub_css.py`
  - **Purpose**: A diagnostic tool that extracts internal .css stylesheet files from all EPUBs in the specified directory.
  - **Use Cases**: When you want to analyze or debug the layout of an EPUB, you can first extract its stylesheets for inspection or use them as a basis for custom styles.
  - **Operation**: After running, input the directory path containing EPUB files. Extracted .css files will be saved in the same directory as the corresponding .epub files.