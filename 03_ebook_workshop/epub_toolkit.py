#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import zipfile
import json

def load_default_path_from_settings():
    """Read default working directory from the shared settings file."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            default_dir = settings.get("default_work_dir")
            return default_dir if default_dir and os.path.isdir(default_dir) else "."
        else:
             return os.path.join(os.path.expanduser("~"), "Downloads")
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Downloads")

def create_epub(src_dir_path, out_file_path):
    """Repack the source folder into an EPUB file."""
    os.makedirs(os.path.dirname(out_file_path), exist_ok=True)

    try:
        with zipfile.ZipFile(out_file_path, "w", zipfile.ZIP_DEFLATED) as zf:
            mimetype_path = os.path.join(src_dir_path, 'mimetype')
            zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)

            for root, _, files in os.walk(src_dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, src_dir_path)
                    
                    if arcname == 'mimetype':
                        continue
                    
                    zf.write(file_path, arcname)
        
        print(f"  ✅ Successfully created: {os.path.basename(out_file_path)}")

    except Exception as e:
        print(f"  ❌ Error occurred while processing '{os.path.basename(src_dir_path)}': {e}")

def unpack_epub_batch(parent_dir):
    """Unpack all EPUB files in the directory (batch)."""
    print("\n--- Mode: Unpack EPUB -> Folder ---")
    
    epub_files = [f for f in os.listdir(parent_dir) if f.lower().endswith('.epub')]
    if not epub_files:
        sys.exit(f"No .epub files found in '{parent_dir}'.")

    print(f"\nFound {len(epub_files)} EPUB file(s) to process.")
    print("--- Starting batch unpack ---")

    for filename in sorted(epub_files):
        print(f"\n--- Processing: {filename} ---")
        epub_path = os.path.join(parent_dir, filename)
        dir_name = os.path.splitext(filename)[0]
        output_dir = os.path.join(parent_dir, dir_name)

        if os.path.exists(output_dir):
            print(f"  ⚠️  Target folder '{dir_name}' already exists; skipping this file.")
            continue

        try:
            os.makedirs(output_dir, exist_ok=True)
            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(output_dir)
            print(f"  ✅ Successfully unpacked to: {dir_name}")
        except Exception as e:
            print(f"  ❌ Error occurred while processing '{filename}': {e}")

    print("\n--- All unpack tasks completed ---")

def repack_epub_batch(parent_dir):
    """Repack all unpacked EPUB folders in the directory (batch)."""
    print("\n--- Mode: Repack Folder -> EPUB ---")
    
    dirs_to_repack = []
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, 'mimetype')):
            dirs_to_repack.append(item_path)
    
    if not dirs_to_repack:
        sys.exit(f"No folders found to repack in '{parent_dir}'.")

    print(f"\nFound {len(dirs_to_repack)} folder(s) to process.")
    print("--- Starting batch repack ---")

    for subdir_path in sorted(dirs_to_repack):
        dir_name = os.path.basename(subdir_path)
        print(f"\n--- Processing: {dir_name} ---")
        
        output_filename = f"{dir_name}.epub"
        output_filepath = os.path.join(parent_dir, output_filename)
        
        if os.path.exists(output_filepath):
            print(f"  ⚠️  Target file '{output_filename}' already exists; skipping this folder.")
            continue

        create_epub(subdir_path, output_filepath)

    print("\n--- All repack tasks completed ---")
    print(f"All repacked EPUB files are saved in the original working directory.")

def main():
    """Main execution function."""
    print("=====================================================")
    print("=      EPUB Unpack & Repack Tool (Batch)      =")
    print("=====================================================")
    
    print(" 1. Unpack EPUB -> Folder")
    print(" 2. Repack Folder -> EPUB")
    print("----------")
    print(" 0. Exit")
    
    mode = input("Select mode: ").strip()

    if mode in ['1', '2']:
        default_path = load_default_path_from_settings()
        prompt_message = (
            f"\nEnter the working directory containing EPUB files (default: {default_path}): " if mode == '1'
            else f"\nEnter the working directory containing unpacked folders (default: {default_path}): "
        )
        parent_dir = input(prompt_message).strip() or default_path

        if not os.path.isdir(parent_dir):
            sys.exit(f"\nError: Directory '{parent_dir}' does not exist.")

        if mode == '1':
            unpack_epub_batch(parent_dir)
        elif mode == '2':
            repack_epub_batch(parent_dir)
            
    elif mode == '0':
        sys.exit("Operation canceled.")
        
    else:
        sys.exit("\nError: Invalid selection. Please enter 1, 2, or 0.")


if __name__ == "__main__":
    main()
