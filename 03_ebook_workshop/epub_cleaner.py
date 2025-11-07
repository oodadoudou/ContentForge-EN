#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB Cleaner
Functionality: Remove covers, font files, and font declarations in CSS styles from EPUB files
Author: ContentForge Project
"""

import os
import sys
import zipfile
import shutil
import tempfile
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

# --- Configuration ---
OUTPUT_DIR_NAME = "processed_files"
DEFAULT_INPUT_PATH = "/Users/doudouda/Downloads/2/"

# Font file extensions
FONT_EXTENSIONS = {
    '.ttf', '.otf', '.woff', '.woff2', '.eot', '.svg'
}

# Regex patterns related to fonts in CSS
FONT_FACE_PATTERN = re.compile(r'@font-face\s*{[^}]*}', re.IGNORECASE | re.DOTALL)
FONT_FAMILY_PATTERN = re.compile(r'font-family\s*:\s*[^;]+;', re.IGNORECASE)
FONT_PATTERN = re.compile(r'font\s*:\s*[^;]+;', re.IGNORECASE)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_unique_filepath(path):
    """Check if a file path exists; if so, append a number to make it unique."""
    if not os.path.exists(path):
        return path
    directory, filename = os.path.split(path)
    name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_name = f"{name} ({counter}){ext}"
        new_path = os.path.join(directory, new_name)
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def load_default_path_from_settings():
    """Read default working directory from the shared settings file."""
    try:
        settings_path = os.path.join(PROJECT_ROOT, 'shared_assets', 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            default_dir = settings.get("default_work_dir")
            return default_dir if default_dir and os.path.isdir(default_dir) else DEFAULT_INPUT_PATH
        else:
            return DEFAULT_INPUT_PATH
    except Exception:
        return DEFAULT_INPUT_PATH

def clean_css_fonts(css_content):
    """
    Clean font-related declarations from CSS content.
    
    Args:
        css_content (str): Original CSS content
        
    Returns:
        tuple: (cleaned CSS content, number of font declarations removed)
    """
    removed_count = 0
    
    # Remove @font-face declarations
    original_content = css_content
    css_content = FONT_FACE_PATTERN.sub('', css_content)
    removed_count += len(FONT_FACE_PATTERN.findall(original_content))
    
    # Remove font-family declarations
    original_content = css_content
    css_content = FONT_FAMILY_PATTERN.sub('', css_content)
    removed_count += len(FONT_FAMILY_PATTERN.findall(original_content))
    
    # Remove font shorthand declarations that include font names (conservative)
    font_matches = FONT_PATTERN.findall(css_content)
    for match in font_matches:
        # Check for common font names or quotes (indicating custom fonts)
        if any(keyword in match.lower() for keyword in ['serif', 'sans-serif', 'monospace', '"', "'"]):
            css_content = css_content.replace(match, '')
            removed_count += 1
    
    # Clean extra blank lines and whitespace
    css_content = re.sub(r'\n\s*\n', '\n', css_content)
    css_content = css_content.strip()
    
    return css_content, removed_count

def remove_cover_from_epub(temp_dir, opf_abs_path, namespaces):
    """
    Remove the cover from an EPUB.
    
    Args:
        temp_dir (str): Temporary extraction directory
        opf_abs_path (str): Absolute path of the OPF file
        namespaces (dict): XML namespaces
        
    Returns:
        tuple: (success, message)
    """
    try:
        opf_tree = ET.parse(opf_abs_path)
        opf_root = opf_tree.getroot()
        opf_dir = os.path.dirname(opf_abs_path)
        
        # Find cover metadata
        meta_cover = opf_root.find('.//opf:meta[@name="cover"]', namespaces)
        if meta_cover is None:
            return True, "Cover metadata not found; skipping cover removal"
        
        cover_id = meta_cover.get('content')
        print(f"  -> Found cover metadata ID: '{cover_id}'")
        
        manifest = opf_root.find('opf:manifest', namespaces)
        if manifest is None:
            return False, "Unable to find manifest node"
        
        # 查找并删除封面图片
        cover_item = manifest.find(f'opf:item[@id="{cover_id}"]', namespaces)
        if cover_item is None:
            return False, f"Unable to find cover item with ID '{cover_id}'"
        
        cover_href = unquote(cover_item.get('href'))
        cover_image_path = os.path.join(opf_dir, cover_href)
        print(f"  -> Found cover image: '{cover_href}'")
        
        # Find and remove cover HTML file
        cover_html_item = None
        html_items = manifest.findall('.//opf:item[@media-type="application/xhtml+xml"]', namespaces)
        for item in html_items:
            html_rel_path = unquote(item.get('href'))
            html_abs_path = os.path.join(opf_dir, html_rel_path)
            if not os.path.exists(html_abs_path):
                continue
            
            try:
                html_tree = ET.parse(html_abs_path)
                # Search for <img> or <svg:image> pointing to the cover
                for img in html_tree.findall('.//xhtml:img', namespaces):
                    if img.get('src') and os.path.basename(unquote(img.get('src'))) == os.path.basename(cover_href):
                        cover_html_item = item
                        break
                if cover_html_item:
                    break
                for img in html_tree.findall('.//svg:image', namespaces):
                    if img.get('{http://www.w3.org/1999/xlink}href') and os.path.basename(unquote(img.get('{http://www.w3.org/1999/xlink}href'))) == os.path.basename(cover_href):
                        cover_html_item = item
                        break
                if cover_html_item:
                    break
            except ET.ParseError:
                continue
        
        # Delete cover HTML file
        if cover_html_item is not None:
            cover_html_id = cover_html_item.get('id')
            cover_html_href = unquote(cover_html_item.get('href'))
            cover_html_path = os.path.join(opf_dir, cover_html_href)
            print(f"  -> Found cover HTML page: '{cover_html_href}'")
            
            # Remove from manifest
            manifest.remove(cover_html_item)
            print("  -> Removed cover HTML from manifest")
            
            # Remove from spine
            spine = opf_root.find('opf:spine', namespaces)
            if spine is not None:
                spine_item = spine.find(f'opf:itemref[@idref="{cover_html_id}"]', namespaces)
                if spine_item is not None:
                    spine.remove(spine_item)
                    print("  -> Removed cover HTML from spine")
            
            # Delete file
            if os.path.exists(cover_html_path):
                os.remove(cover_html_path)
                print("  -> Deleted cover HTML file")
        
        # 删除封面图片文件
        if os.path.exists(cover_image_path):
            os.remove(cover_image_path)
            print(f"  -> Deleted cover image: {os.path.basename(cover_image_path)}")
        
        # 从 manifest 中删除封面图片项目
        manifest.remove(cover_item)
        print("  -> Removed cover image from manifest")
        
        # 删除封面元数据
        metadata = opf_root.find('opf:metadata', namespaces)
        if metadata is not None:
            metadata.remove(meta_cover)
            print("  -> Deleted cover metadata")
        
        # 保存修改后的 OPF 文件
        opf_tree.write(opf_abs_path, encoding='utf-8', xml_declaration=True)
        
        return True, "Cover removed successfully"
    
    except Exception as e:
        return False, f"Error while removing cover: {e}"

def remove_fonts_from_epub_content(temp_dir):
    """
    Remove font files and font declarations in CSS from extracted EPUB content.
    
    Args:
        temp_dir (str): Temporary extraction directory
        
    Returns:
        tuple: (number of font files removed, number of CSS files processed, number of CSS declarations removed)
    """
    font_files_removed = 0
    css_files_processed = 0
    total_css_declarations_removed = 0
    
    # Scan and remove font files
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            if file_ext in FONT_EXTENSIONS:
                os.remove(file_path)
                font_files_removed += 1
                print(f"  -> Deleted font file: {os.path.relpath(file_path, temp_dir)}")
    
    # Process CSS files
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.css'):
                css_file_path = os.path.join(root, file)
                
                try:
                    with open(css_file_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    cleaned_content, removed_count = clean_css_fonts(original_content)
                    
                    if removed_count > 0:
                        with open(css_file_path, 'w', encoding='utf-8') as f:
                            f.write(cleaned_content)
                        
                        css_files_processed += 1
                        total_css_declarations_removed += removed_count
                        print(f"  -> Cleaned CSS file: {os.path.relpath(css_file_path, temp_dir)} (removed {removed_count} font declaration(s))")
                
                except UnicodeDecodeError:
                    print(f"  -> Warning: Unable to read CSS file {file} (encoding issue)")
                except Exception as e:
                    print(f"  -> Warning: Error processing CSS file {file}: {e}")
    
    return font_files_removed, css_files_processed, total_css_declarations_removed

def process_single_epub(epub_path, output_dir, mode):
    """
    Process a single EPUB file.
    
    Args:
        epub_path (str): Path to the EPUB file
        output_dir (str): Output directory
        mode (str): Processing mode ('c'=cover, 'f'=fonts, 'b'=both)
        
    Returns:
        bool: Whether processing succeeded
    """
    base_name = os.path.basename(epub_path)
    output_epub_path = get_unique_filepath(os.path.join(output_dir, base_name))
    
    # 创建临时目录
    temp_extract_dir = tempfile.mkdtemp(prefix=f"{os.path.splitext(base_name)[0]}_")
    
    print(f"\n[+] Processing: {base_name}")
    
    try:
        # 1. 解压 EPUB 文件
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
            print(f"  -> Extracted to temporary directory")
        
        # 2. 根据模式处理内容
        cover_success = True
        cover_info = ""
        font_files_removed = 0
        css_files_processed = 0
        total_css_declarations_removed = 0
        
        if mode in ['c', 'b']:  # Process cover
            # Find OPF file
            container_path = os.path.join(temp_extract_dir, 'META-INF', 'container.xml')
            if os.path.exists(container_path):
                container_tree = ET.parse(container_path)
                container_root = container_tree.getroot()
                ns_cn = {'cn': 'urn:oasis:names:tc:opendocument:xmlns:container'}
                opf_path_element = container_root.find('cn:rootfiles/cn:rootfile', ns_cn)
                
                if opf_path_element is not None:
                    opf_rel_path = opf_path_element.get('full-path')
                    opf_abs_path = os.path.join(temp_extract_dir, opf_rel_path)
                    
                    # 定义命名空间
                    namespaces = {
                        'opf': 'http://www.idpf.org/2007/opf',
                        'dc': 'http://purl.org/dc/elements/1.1/',
                        'xhtml': 'http://www.w3.org/1999/xhtml',
                        'svg': 'http://www.w3.org/2000/svg',
                        'xlink': 'http://www.w3.org/1999/xlink'
                    }
                    for prefix, uri in namespaces.items():
                        ET.register_namespace(prefix, uri)
                    
                    cover_success, cover_info = remove_cover_from_epub(temp_extract_dir, opf_abs_path, namespaces)
                    print(f"  -> {cover_info}")
                else:
                    print("  -> Warning: Unable to find OPF file path")
            else:
                print("  -> Warning: Unable to find container.xml file")
        
        if mode in ['f', 'b']:  # 处理字体
            font_files_removed, css_files_processed, total_css_declarations_removed = remove_fonts_from_epub_content(temp_extract_dir)
        
        # 3. 重新打包 EPUB
        print(f"  -> Repacking...")
        with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            # 首先添加 mimetype 文件（必须不压缩）
            mimetype_path = os.path.join(temp_extract_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zip_out.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            else:
                print("  -> Warning: 'mimetype' file not found")
            
            # 添加其他文件
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    if file == 'mimetype':
                        continue
                    
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):  # 确保文件存在（可能已被删除）
                        arcname = os.path.relpath(file_path, temp_extract_dir)
                        zip_out.write(file_path, arcname)
        
        # 4. 显示处理结果
        print(f"  -> Processing complete!")
        if mode in ['c', 'b']:
            print(f"     Cover processing: {cover_info}")
        if mode in ['f', 'b']:
            print(f"     Font files removed: {font_files_removed}")
            print(f"     CSS files processed: {css_files_processed}")
            print(f"     Font declarations removed: {total_css_declarations_removed}")
        print(f"     Output file: {os.path.relpath(output_epub_path)}")
        
        return True
        
    except zipfile.BadZipFile:
        print(f"  -> Error: '{base_name}' is not a valid ZIP/EPUB file")
        return False
    except Exception as e:
        print(f"  -> Error: Exception occurred while processing '{base_name}': {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean temporary files
        if temp_extract_dir and os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)

def process_epub_directory(input_dir, mode):
    """
    Process all EPUB files in the specified directory.
    
    Args:
        input_dir (str): Input directory path
        mode (str): Processing mode ('c'=cover, 'f'=fonts, 'b'=both)
    """
    print("=" * 60)
    print("           EPUB Cleaner")
    print("=" * 60)
    
    mode_desc = {
        'c': 'Remove cover',
        'f': 'Remove fonts',
        'b': 'Remove cover and fonts'
    }
    print(f"Mode: {mode_desc.get(mode, 'Unknown')}")
    
    # 创建输出目录
    output_dir = os.path.join(input_dir, OUTPUT_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nScanning directory: {os.path.abspath(input_dir)}")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    
    # Find all EPUB files
    epub_files = [f for f in os.listdir(input_dir) 
                  if f.lower().endswith('.epub') and os.path.isfile(os.path.join(input_dir, f))]
    
    if not epub_files:
        print("\nNo .epub files found in the specified directory.")
        return
    
    print(f"\nFound {len(epub_files)} EPUB file(s) to process")
    print("-" * 60)
    
    # 处理每个 EPUB 文件
    success_count = 0
    fail_count = 0
    
    for epub_file in sorted(epub_files):
        epub_full_path = os.path.join(input_dir, epub_file)
        if process_single_epub(epub_full_path, output_dir, mode):
            success_count += 1
        else:
            fail_count += 1
    
    # Show processing results
    print("\n" + "=" * 60)
    print("                Completed")
    print("=" * 60)
    print(f"Total: {len(epub_files)} file(s)")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"\nProcessed files saved in: {os.path.abspath(output_dir)}")

def get_processing_mode():
    """
    Get the processing mode selected by the user.
    
    Returns:
        str: Processing mode ('c', 'f', 'b')
    """
    print("\n" + "=" * 60)
    print("           Select Processing Mode")
    print("=" * 60)
    print("ℹ️  Please choose an action:")
    print("   [f] Remove fonts - delete font files and font declarations from CSS")
    print("   [c] Remove cover - delete cover image and cover page")
    print("   [b] Remove both - delete cover and fonts")
    print("-" * 60)
    
    while True:
        choice = input("Enter option (f/c/b): ").strip().lower()
        if choice in ['f', 'c', 'b']:
            return choice
        else:
            print("❌ Invalid option, please enter f, c, or b")

def main():
    """Main function"""
    print("=" * 60)
    print("           EPUB Cleaner")
    print("=" * 60)
    print("Feature: Remove covers, font files, and font declarations in CSS from EPUB files")
    
    # 1. 获取处理模式
    mode = get_processing_mode()
    
    # 2. 获取目录路径
    default_path = load_default_path_from_settings()
    prompt_message = (
        f"\nPlease enter the directory path that contains EPUB files\n"
        f"(Press Enter to use the default path: {default_path}): "
    )
    
    user_input = input(prompt_message).strip().strip('"\'')
    target_dir = user_input if user_input else default_path
    
    if not user_input:
        print(f"Using default directory: {target_dir}")
    
    # 3. 验证目录
    if not os.path.isdir(target_dir):
        print(f"\n❌ Error: Directory '{target_dir}' does not exist or is not valid.")
        sys.exit(1)
    
    # 4. 开始处理
    process_epub_directory(target_dir, mode)

if __name__ == "__main__":
    main()