import os
import sys
import zipfile
import tempfile
import re
from xml.etree import ElementTree as ET
import json

# Import OpenCC; if import fails, provide clear installation guidance
try:
    from opencc import OpenCC
    # 导入模块本身以获取其路径
    import opencc as opencc_module
except ImportError:
    print("Error: Failed to import OpenCC. Please install: pip install opencc-python-reimplemented", file=sys.stderr)
    sys.exit(1)

def check_epub_needs_processing(epub_path, cc):
    """
    Check whether an EPUB file needs processing.
    Returns: (needs_layout_change, needs_char_conversion)
    """
    needs_layout_change = False
    needs_char_conversion = False
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            opf_path = find_opf_file(temp_dir)
            if not opf_path:
                return False, False

            # 1. Check whether layout conversion is needed (vertical -> horizontal)
            tree = ET.parse(opf_path)
            root = tree.getroot()
            ns = {'opf': 'http://www.idpf.org/2007/opf'}
            spine = root.find('opf:spine', ns)
            if spine is not None and spine.get('page-progression-direction') == 'rtl':
                needs_layout_change = True
            
            # --- START: Optimized Traditional/Simplified content detection ---
            for root_dir, _, files in os.walk(temp_dir):
                content_files = [f for f in files if f.endswith(('.xhtml', '.html', '.opf'))]
                if not content_files:
                    continue
                
                for filename in content_files:
                    sample_file_path = os.path.join(root_dir, filename)
                    sample_text = ""
                    try:
                        with open(sample_file_path, 'r', encoding='utf-8') as f:
                            sample_text = f.read(2048)
                    except UnicodeDecodeError:
                        try:
                            with open(sample_file_path, 'r', encoding='gbk', errors='ignore') as f:
                                sample_text = f.read(2048)
                        except Exception:
                            continue
                    
                    if sample_text and sample_text != cc.convert(sample_text):
                        needs_char_conversion = True
                        break
                
                if needs_char_conversion:
                    break
            # --- END: Optimized Traditional/Simplified content detection ---

    except Exception:
        return False, False

    return needs_layout_change, needs_char_conversion


def find_opf_file(temp_dir):
    """Find the .opf file path in the unpacked directory."""
    for root, _, files in os.walk(temp_dir):
        for filename in files:
            if filename.endswith('.opf'):
                return os.path.join(root, filename)
    return None

def modify_opf_file(opf_path, cc, do_layout, do_chars):
    """Modify the .opf file to convert layout and/or text as needed."""
    if not do_layout and not do_chars:
        return
    try:
        ET.register_namespace('dc', "http://purl.org/dc/elements/1.1/")
        ET.register_namespace('opf', "http://www.idpf.org/2007/opf")
        tree = ET.parse(opf_path)
        root = tree.getroot()
        ns = {'opf': 'http://www.idpf.org/2007/opf', 'dc': 'http://purl.org/dc/elements/1.1/'}

        if do_layout:
            spine = root.find('opf:spine', ns)
            if spine is not None:
                spine.set('page-progression-direction', 'ltr')
                print("  - [Layout] Page progression direction -> 'ltr'.")

        if do_chars:
            metadata = root.find('opf:metadata', ns)
            if metadata is not None:
                for elem in metadata.iter():
                    if elem.text and elem.text.strip():
                        elem.text = cc.convert(elem.text)
                    if elem.tail and elem.tail.strip():
                        elem.tail = cc.convert(elem.tail)
                print("  - [Text] Book metadata -> Simplified Chinese.")

        if sys.version_info >= (3, 9):
            ET.indent(tree)
        tree.write(opf_path, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        print(f"  - [Error] Failed to modify OPF file: {e}")

def modify_content_files(temp_dir, cc, do_layout, do_chars):
    """Modify content files to convert layout and/or text as needed."""
    for root_dir, _, files in os.walk(temp_dir):
        for filename in files:
            if not filename.endswith(('.xhtml', '.html', '.css', '.ncx')):
                continue

            file_path = os.path.join(root_dir, filename)
            try:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                        content = f.read()
                        
                original_content = content
                
                if do_layout and filename.endswith('.css'):
                    content = content.replace('vertical-rl', 'horizontal-tb')
                    content = content.replace(".vrtl", ".hltr")
                    content = re.sub(r'local\("@(.*?)"\)', r'local("\1")', content)

                if filename.endswith(('.xhtml', '.html', '.ncx')):
                    if do_layout:
                         content = content.replace('class="vrtl"', 'class="hltr"')
                    if do_chars:
                        content = cc.convert(content)

                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  - [Modified] Updated: {os.path.relpath(file_path, temp_dir)}")
            except Exception as e:
                print(f"  - [Error] Failed to process file {filename}: {e}")

def repack_epub(temp_dir, new_epub_path):
    """Repack modified files into an EPUB."""
    try:
        mimetype_path = os.path.join(temp_dir, 'mimetype')
        with zipfile.ZipFile(new_epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            for root_dir, _, files in os.walk(temp_dir):
                for filename in files:
                    if filename != 'mimetype':
                        file_path = os.path.join(root_dir, filename)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zf.write(file_path, arcname)
        print(f"  -> [Success] New file saved to: {os.path.basename(os.path.dirname(new_epub_path))}{os.sep}{os.path.basename(new_epub_path)}")
    except Exception as e:
        print(f"  - [Error] Failed to repack EPUB: {e}")

def process_epub_file(epub_path, output_dir, cc):
    """Process a single EPUB file, including detection and conversions as needed."""
    print(f"\n[Check] {os.path.basename(epub_path)}")
    needs_layout, needs_chars = check_epub_needs_processing(epub_path, cc)

    if not needs_layout and not needs_chars:
        print("  - [Skip] No conversions needed.")
        return

    print(f"  - [Task] Required: {'Layout conversion ' if needs_layout else ''}{'Character conversion' if needs_chars else ''}")
    
    base_name, _ = os.path.splitext(os.path.basename(epub_path))
    new_epub_path = os.path.join(output_dir, f"{base_name}.epub")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            opf_path = find_opf_file(temp_dir)
            if not opf_path:
                print("  - [Error] .opf configuration file not found!")
                return

            modify_opf_file(opf_path, cc, needs_layout, needs_chars)
            modify_content_files(temp_dir, cc, needs_layout, needs_chars)
            repack_epub(temp_dir, new_epub_path)

        except Exception as e:
            print(f"  - [Critical] Unknown error while processing EPUB: {e}")
            
def process_txt_file(txt_path, output_dir, cc):
    """Process a single TXT file; perform Traditional → Simplified conversion only."""
    print(f"\n[Process TXT] {os.path.basename(txt_path)}")
    try:
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(txt_path, 'r', encoding='gbk', errors='ignore') as f:
                content = f.read()
        
        converted_content = cc.convert(content)

        if content == converted_content:
            print("  - [Skip] TXT file conversion not needed.")
            return
            
        new_txt_path = os.path.join(output_dir, os.path.basename(txt_path))
        with open(new_txt_path, 'w', encoding='utf-8') as f:
            f.write(converted_content)
        print(f"  -> [Success] New file saved to: {os.path.basename(output_dir)}{os.sep}{os.path.basename(new_txt_path)}")

    except Exception as e:
        print(f"  - [Error] Error while processing TXT file: {e}")

def initialize_opencc():
    """Initialize OpenCC converter with robust fallback options."""
    try:
        return OpenCC('t2s')
    except Exception as e_simple:
        print("[Warning] Standard OpenCC initialization failed; attempting fallback...")
        try:
            package_path = opencc_module.__path__[0]
            
            possible_paths = [
                os.path.join(package_path, 'data', 'config', 't2s.json'),
                os.path.join(package_path, 'config', 't2s.json'),
                os.path.join(package_path, 't2s.json')
            ]
            
            config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if not config_path:
                 raise FileNotFoundError("Could not find config file (t2s.json) in OpenCC package directory.")

            print(f"[Info] Found configuration file path: {config_path}")
            return OpenCC(config_path)
            
        except Exception as e_fallback:
            print("Error: Unable to initialize OpenCC converter.", file=sys.stderr)
            print("Both standard and fallback modes failed. This may be due to an incomplete installation or permission issues.", file=sys.stderr)
            print(f"\n- Standard mode error: {e_simple}", file=sys.stderr)
            print(f"- Fallback mode error: {e_fallback}", file=sys.stderr)
            print("\nTry uninstalling and reinstalling: pip uninstall opencc-python-reimplemented -y && pip install opencc-python-reimplemented", file=sys.stderr)
            sys.exit(1)

# --- Added: function to load default path from settings.json ---
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
    """Script entry point."""
    cc = initialize_opencc()
    print("[Info] OpenCC initialized successfully.")

    # --- 修改：动态加载默认路径 ---
    default_path = load_default_path_from_settings()
    prompt_message = f"Please enter the target root directory (Press Enter to use: {default_path}): "
    target_directory = input(prompt_message).strip() or default_path

    if not os.path.isdir(target_directory):
        print(f"Error: Directory '{target_directory}' does not exist or is invalid.", file=sys.stderr)
        sys.exit(1)
        
    output_dir = os.path.join(target_directory, "processed_files")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[*] Starting to scan directory: {os.path.abspath(target_directory)}")
    print(f"[*] All processed files will be saved to: {output_dir}")
    
    for root, _, files in os.walk(target_directory):
        if os.path.abspath(root).startswith(os.path.abspath(output_dir)):
            continue

        for filename in files:
            file_path = os.path.join(root, filename)
            if filename.endswith('.epub'):
                process_epub_file(file_path, output_dir, cc)
            elif filename.endswith('.txt'):
                process_txt_file(file_path, output_dir, cc)
    
    print("\n[*] All operations completed.")

if __name__ == "__main__":
    main()