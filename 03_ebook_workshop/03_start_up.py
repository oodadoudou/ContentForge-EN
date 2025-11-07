import os
import sys

# 将项目根目录添加到Python搜索路径中，以便能导入共享工具
# This assumes the script is in a subdirectory of the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import utils

def menu_ebook_workshop():
    """Module 03: Standalone menu for eBook processing and generation"""
    module_path = '03_ebook_workshop'
    
    # 加载全局设置
    settings = utils.load_settings()
    
    while True:
        utils.print_header("3. eBook Processing & Generation (TXT/EPUB/HTML)")
        print("--- Create & Convert ---")
        print(" 1. [Create] Build EPUB with chapter TOC from TXT (⭐ New style selection)")
        print("    └ Features: Intelligent chapter detection + 5 elegant styles + live preview + custom cover")
        print(" 2. [Create] Batch convert Markdown folder to HTML")
        print(" 3. [Convert] Extract plain text (TXT) from EPUB")
        
        print("\n--- Edit & Repair EPUB ---")
        print(" 4. (Metadata) Batch rename EPUB files")
        print("    └ Feature: Read internal EPUB title; manually edit or auto-normalize filenames.")
        print(" 5. (Content) Convert EPUB content to Simplified Chinese only")
        print("    └ Feature: Only Traditional→Simplified conversion; layout unchanged.")
        print(" 6. (Comprehensive) Fix vertical layout and convert to Simplified Chinese (Recommended)")
        print("    └ Feature: Auto-detect and correct vertical layout and Traditional content in one go.")
        print(" 7. (Cleanup) EPUB cleaner (covers/fonts)")
        print("    └ Feature: Remove covers, font files, and CSS font declarations; supports standalone or combined ops.")
        
        print("\n--- Advanced Tools ---")
        print(" 8. Batch replace EPUB/TXT content by rules")
        print(" 9. Beautify EPUB with unified CSS style")
        print(" 10. Split EPUB into equal parts by chapter count")
        print(" 11. Merge all EPUBs in a folder")
        print(" 12. [Utility] EPUB unpack/pack toolkit")
        print("     └ Feature: Batch unzip EPUBs for editing or repackage from folder into EPUB.")
        print(" 13. Punctuation completion tool (TXT/EPUB)")
        print("     └ Feature: Intelligently add missing commas in Chinese text; skip non-body content.")

        print("----------")
        print(" 88. View module usage (README)")
        print(" 0. Return to main menu")
        choice = utils.get_input("Please choose")

        if choice == '1':
            utils.run_script("txt_to_epub_convertor.py", cwd=module_path)
        elif choice == '2':
            utils.run_script("convert_md_to_html.py", cwd=module_path)
        elif choice == '3':
            utils.run_script("epub_to_txt_convertor.py", cwd=module_path)
        elif choice == '4':
            utils.run_script("epub_rename.py", cwd=module_path)
        elif choice == '5':
            utils.run_script("epub_convert_tc_to_sc.py", cwd=module_path)
        elif choice == '6':
            utils.run_script("epub_reformat_and_convert_v2.py", cwd=module_path)
        elif choice == '7':
            utils.run_script("epub_cleaner.py", cwd=module_path)
        elif choice == '8':
            utils.run_script("batch_replacer_v2.py", cwd=module_path)
        elif choice == '9':
            utils.run_script("epub_styler.py", cwd=module_path)
        elif choice == '10':
            utils.run_script("split_epub.py", cwd=module_path)
        elif choice == '11':
            utils.run_script("epub_merge.py", cwd=module_path)
        elif choice == '12':
            utils.run_script("epub_toolkit.py", cwd=module_path)
        elif choice == '13':
            print("\nSelect punctuation completion mode:")
            print(" 1. Add commas only (Recommended, safe)")
            print(" 2. Advanced: Add more dialogue symbols (may be incorrect)")
            mode = utils.get_input("Enter mode number (1/2)")
            print("\nTip:\nAfter completion, use 4. File Repair & Tools → 3. Fix missing CSS links in EPUB to resolve potential CSS loss issues.\n")
            if mode == '2':
                utils.run_script("punctuation_fixer_v2.py", cwd=module_path)
            else:
                utils.run_script("punctuation_fixer.py", cwd=module_path)
        elif choice == '88':
            utils.show_usage(module_path)
        elif choice == '0':
            # Return to main menu (exit from sub-menu)
            break

if __name__ == "__main__":
    try:
        menu_ebook_workshop()
    except KeyboardInterrupt:
        # Graceful exit when user presses Ctrl+C within the sub-menu
        print("\n\nOperation interrupted by user.")
        sys.exit(0)