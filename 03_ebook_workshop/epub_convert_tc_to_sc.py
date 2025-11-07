import os
import sys
import zipfile
import tempfile
import re
from xml.etree import ElementTree as ET
import json

# Import OpenCC module; provide clear installation guidance if import fails
try:
    from opencc import OpenCC
    # 导入模块本身以获取其路径
    import opencc as opencc_module
except ImportError:
    print("Error: Unable to import OpenCC. Please install: pip install opencc-python-reimplemented", file=sys.stderr)
    sys.exit(1)

def initialize_opencc():
    """Initialize the OpenCC converter with robust fallback options."""
    try:
        # Prefer standard initialization without .json suffix
        return OpenCC('t2s')
    except Exception as e_simple:
        print("[Warning] Standard OpenCC initialization failed; trying fallback...")
        try:
            package_path = opencc_module.__path__[0]
            config_path = os.path.join(package_path, 'config', 't2s.json')
            
            if not os.path.exists(config_path):
                 raise FileNotFoundError("Could not find config file (t2s.json) in the OpenCC package directory.")

            print(f"[Info] Located config file path: {config_path}")
            return OpenCC(config_path)
            
        except Exception as e_fallback:
            print("Error: Unable to initialize OpenCC converter.", file=sys.stderr)
            print("Both standard and fallback modes failed.", file=sys.stderr)
            print(f"\n- Standard mode error: {e_simple}", file=sys.stderr)
            print(f"- Fallback mode error: {e_fallback}", file=sys.stderr)
            sys.exit(1)

def check_if_translation_needed(temp_dir, cc):
    """
    Check whether the EPUB contains content that needs conversion to Simplified Chinese.
    """
    for root, _, files in os.walk(temp_dir):
        # Prioritize content files
        content_files = [f for f in files if f.endswith(('.xhtml', '.html', '.opf'))]
        if not content_files:
            continue
        
        # Sample and check the first content file found
        sample_file_path = os.path.join(root, content_files[0])
        try:
            with open(sample_file_path, 'r', encoding='utf-8') as f:
                sample_text = f.read(2048)  # 读取 2KB 样本
                if sample_text != cc.convert(sample_text):
                    return True # Traditional characters detected; conversion needed
        except Exception:
            continue # 如果读取失败，尝试下一个文件
            
    return False # No conversion needed

def translate_text_files_in_epub(temp_dir, cc):
    """
    Iterate the temporary directory and translate the content of all text files.
    """
    # File types to process
    text_extensions = ('.xhtml', '.html', '.opf', '.ncx', '.css')
    
    for root, _, files in os.walk(temp_dir):
        for filename in files:
            if filename.endswith(text_extensions):
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Only convert content for XML/HTML types; skip CSS
                    if not filename.endswith('.css'):
                        converted_content = cc.convert(content)
                    else:
                        converted_content = content

                    # 仅当内容有变化时才写回文件
                    if converted_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(converted_content)
                        print(f"  - [Translate] Updated file: {os.path.relpath(file_path, temp_dir)}")
                        
                except Exception as e:
                    print(f"  - [Warning] Skipped file {filename}; reason: {e}")

def repack_epub(temp_dir, new_epub_path):
    """
    Repack the modified files into an EPUB.
    """
    try:
        mimetype_path = os.path.join(temp_dir, 'mimetype')
        with zipfile.ZipFile(new_epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # mimetype 文件必须是第一个且不能压缩
            zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            for root_dir, _, files in os.walk(temp_dir):
                for filename in files:
                    if filename != 'mimetype':
                        file_path = os.path.join(root_dir, filename)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zf.write(file_path, arcname)
        print(f"  -> [Success] New file saved: {os.path.basename(new_epub_path)}")
    except Exception as e:
        print(f"  - [Error] Failed to repack EPUB: {e}")

def process_epub(epub_path, output_dir, cc):
    """
    Full workflow for processing a single EPUB: extract, detect, translate, repack.
    """
    print(f"\n[Check] {os.path.basename(epub_path)}")
    
    # 在临时目录中解压并检查
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(temp_dir)

            if not check_if_translation_needed(temp_dir, cc):
                print("  - [Skip] Content is already Simplified or does not require conversion.")
                return

            print("  - [Task] Traditional content detected; starting conversion...")
            
            # 翻译所有文本文件
            translate_text_files_in_epub(temp_dir, cc)

            # 创建新文件名并打包
            base_name, _ = os.path.splitext(os.path.basename(epub_path))
            new_epub_path = os.path.join(output_dir, f"{base_name}-zhCN.epub")
            repack_epub(temp_dir, new_epub_path)

        except zipfile.BadZipFile:
            print(f"  - [Error] '{os.path.basename(epub_path)}' is not a valid EPUB file.")
        except Exception as e:
            print(f"  - [Critical] Unknown issue occurred while processing EPUB: {e}")

# --- Added: Function to load default path from settings.json ---
def load_default_path_from_settings():
    """Read default working directory from the shared settings file."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        default_dir = settings.get("default_work_dir")
        return default_dir if default_dir else "."
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Downloads")

def main():
    """
    Script entry point.
    """
    cc = initialize_opencc()
    print("[Info] OpenCC initialized successfully.")

    # --- 修改：动态加载默认路径 ---
    default_path = load_default_path_from_settings()
    prompt_message = f"Please enter the root directory containing EPUB files (Press Enter to use: {default_path}): "
    target_directory = input(prompt_message).strip() or default_path

    if not os.path.isdir(target_directory):
        print(f"Error: Directory '{target_directory}' does not exist or is invalid.", file=sys.stderr)
        sys.exit(1)
        
    output_dir = os.path.join(target_directory, "translated_files")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[*] Starting scan of directory: {os.path.abspath(target_directory)}")
    print(f"[*] All translated files will be saved to: {os.path.abspath(output_dir)}")
    
    for root, _, files in os.walk(target_directory):
        if os.path.abspath(root).startswith(os.path.abspath(output_dir)):
            continue

        for filename in files:
            if filename.endswith('.epub'):
                # 避免处理已经转换过的文件
                if '-zhCN' in filename:
                    continue
                file_path = os.path.join(root, filename)
                process_epub(file_path, output_dir, cc)
    
    print("\n[*] All operations completed.")

if __name__ == "__main__":
    main()
