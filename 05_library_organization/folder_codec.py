#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import json
import time
import zipfile
import threading
import itertools
import subprocess

# --- Global availability check for native command-line tools ---
NATIVE_7Z_PATH = shutil.which('7z')
NATIVE_ZIP_PATH = shutil.which('zip')
NATIVE_UNZIP_PATH = shutil.which('unzip')

try:
    import py7zr
    PYTHON_LIBS_AVAILABLE = True
except ImportError:
    PYTHON_LIBS_AVAILABLE = False


def run_native_command_with_spinner(command, msg):
    """Runs a native command-line process and shows a spinner."""
    spinner = itertools.cycle(['-', '\\', '|', '/'])
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    sys.stdout.write(f"  -> {msg}...  ")
    sys.stdout.flush()

    while process.poll() is None:
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        time.sleep(0.1)
        sys.stdout.write('\b')
    
    stderr = process.communicate()[1]
    if process.returncode != 0:
        sys.stdout.write("❌ Failed\n")
        if isinstance(stderr, bytes):
            try:
                stderr = stderr.decode(sys.getdefaultencoding(), errors='ignore')
            except Exception:
                stderr = str(stderr)
        sys.stderr.write(f"     Error details: {stderr.strip()}\n")
        return False
    else:
        sys.stdout.write("✓ Done\n")
        return True

def run_python_func_with_spinner(target_func, msg):
    """Runs a Python function in a separate thread and shows a spinner."""
    exception_container = []
    
    def target_wrapper():
        try:
            target_func()
        except Exception as e:
            exception_container.append(e)

    thread = threading.Thread(target=target_wrapper)
    thread.start()
    
    spinner = itertools.cycle(['-', '\\', '|', '/'])
    sys.stdout.write(f"  -> {msg}...  ")
    sys.stdout.flush()
    
    while thread.is_alive():
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        time.sleep(0.1)
        sys.stdout.write('\b')
    
    thread.join()

    if exception_container:
        sys.stdout.write("❌ Failed\n")
        sys.stderr.write(f"     Error details: {exception_container[0]}\n")
        return False
    else:
        sys.stdout.write("✓ Done\n")
        return True

def load_default_path_from_settings():
    """Read the default working directory from the shared settings file."""
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

def _pack_directory(full_dir_path, parent_dir):
    """Pack a single directory, preferring native commands when available."""
    dir_name = os.path.basename(full_dir_path)
    temp_7z_path = os.path.join(parent_dir, f"{dir_name}.7z")
    renamed_7z_path = os.path.join(parent_dir, f"{dir_name}.7删z")
    final_zip_path = os.path.join(parent_dir, f"{dir_name}.z删ip")

    try:
        if NATIVE_7Z_PATH and NATIVE_ZIP_PATH:
            cmd_7z = [NATIVE_7Z_PATH, 'a', '-p1111', temp_7z_path, full_dir_path]
            if not run_native_command_with_spinner(cmd_7z, "Step A: 7z encrypted compression"): return False
            
            print(f"  -> Step B: Rename to .7删z...", end=''); shutil.move(temp_7z_path, renamed_7z_path); print(" ✓ Done")

            original_cwd = os.getcwd()
            os.chdir(parent_dir)
            cmd_zip = [NATIVE_ZIP_PATH, '-q', '-j', os.path.basename(final_zip_path), os.path.basename(renamed_7z_path)]
            if not run_native_command_with_spinner(cmd_zip, "Step C: ZIP secondary compression"):
                os.chdir(original_cwd); return False
            os.chdir(original_cwd)
        else:
            def create_7z():
                with py7zr.SevenZipFile(temp_7z_path, 'w', password='1111') as archive:
                    archive.writeall(full_dir_path, arcname=dir_name)
            if not run_python_func_with_spinner(create_7z, "Step A: 7z encrypted compression"): return False

            print(f"  -> Step B: Rename to .7删z...", end=''); shutil.move(temp_7z_path, renamed_7z_path); print(" ✓ Done")

            print("  -> Step C: ZIP secondary compression...", end='')
            with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(renamed_7z_path, arcname=os.path.basename(renamed_7z_path))
            print(" ✓ Done")

    except Exception as e:
        print(f" ❌ Processing failed\nError: {e}")
        if os.path.exists(temp_7z_path): os.remove(temp_7z_path)
        if os.path.exists(renamed_7z_path): os.remove(renamed_7z_path)
        return False
    finally:
        if os.path.exists(renamed_7z_path):
            print(f"  -> Step D: Clean up temporary files...", end=''); os.remove(renamed_7z_path); print(" ✓ Done")
            
    return True

def encode_items_in_dir(parent_dir):
    """Encryption packing mode, preserves source files."""
    print("\n--- Mode: Encrypt & Pack (files/folders -> .z删ip) ---")
    items_to_process = [item for item in os.listdir(parent_dir) if not item.endswith(('.z删ip', '.zip', '.7z')) and not item.startswith('.')]
    if not items_to_process: sys.exit(f"No files or folders to process found in '{parent_dir}'.")
    
    total_items = len(items_to_process)
    print(f"\nFound {total_items} items to process.")
    
    for i, item_name in enumerate(sorted(items_to_process)):
        item_path = os.path.join(parent_dir, item_name)
        dir_to_pack, temp_folder_path = None, None
        
        print(f"\n--- Processing: {item_name} ({i+1}/{total_items}) ---")

        if os.path.isdir(item_path):
            dir_to_pack = item_path
        elif os.path.isfile(item_path):
            folder_name = os.path.splitext(item_name)[0]
            new_folder_path = os.path.join(parent_dir, f"{folder_name}_pack_temp_{int(time.time())}")
            if os.path.exists(new_folder_path):
                print(f"  [!] Warning: Temporary folder '{new_folder_path}' already exists, skipping."); continue
            try:
                print(f"  -> Preprocess: Create temporary folder...", end=''); os.makedirs(new_folder_path); print(" ✓ Done")
                print(f"  -> Preprocess: Copy file into folder...", end=''); shutil.copy(item_path, new_folder_path); print(" ✓ Done")
                dir_to_pack, temp_folder_path = new_folder_path, new_folder_path
            except Exception as e:
                print(f" ❌ Failed\nError: File preprocessing failed: {e}", file=sys.stderr)
                if os.path.exists(new_folder_path): shutil.rmtree(new_folder_path)
                continue
        
        if dir_to_pack:
            _pack_directory(dir_to_pack, parent_dir)
            if temp_folder_path:
                print(f"  -> Clean up temporary folder...", end=''); shutil.rmtree(temp_folder_path); print(" ✓ Done")
    print("\n--- All encryption packing tasks completed ---")

def decode_files_in_dir(parent_dir):
    """Decrypt and restore mode, preferring native commands when available."""
    print("\n--- Mode: Decrypt & Restore (.z删ip -> folder) ---")
    target_files = [f for f in os.listdir(parent_dir) if '删' in f and f.endswith('.z删ip')]
    if not target_files: sys.exit(f"No files containing '删' found in '{parent_dir}'.")

    total_files = len(target_files)
    print(f"\nFound {total_files} files to process.")
    
    for i, filename in enumerate(sorted(target_files)):
        print(f"\n--- Processing: {filename} ({i+1}/{total_files}) ---")
        full_file_path = os.path.join(parent_dir, filename)
        inner_7z_path, temp_zip_path = "", ""
        
        try:
            if NATIVE_UNZIP_PATH and NATIVE_7Z_PATH:
                temp_zip_path = os.path.join(parent_dir, filename.replace('.z删ip', '.zip'))
                shutil.copy(full_file_path, temp_zip_path)
                
                cmd_unzip = [NATIVE_UNZIP_PATH, '-o', temp_zip_path, '-d', parent_dir]
                if not run_native_command_with_spinner(cmd_unzip, "Step 1: Extracting ZIP"): continue

                inner_7z_renamed_path = os.path.join(parent_dir, filename.replace('z删ip', '7删z'))
                inner_7z_path = inner_7z_renamed_path.replace('.7删z', '.7z')
                shutil.move(inner_7z_renamed_path, inner_7z_path)

                target_dir_name = os.path.splitext(os.path.basename(inner_7z_path))[0]
                cmd_7z_extract = [NATIVE_7Z_PATH, 'x', f'-p1111', f'-o{os.path.join(parent_dir, target_dir_name)}', '-y', inner_7z_path]
                if not run_native_command_with_spinner(cmd_7z_extract, "Step 2: Extracting 7Z"): continue
            else:
                print(f"  -> Step 1: Extracting ZIP...", end='')
                with zipfile.ZipFile(full_file_path, 'r') as zf:
                    if not zf.namelist(): raise ValueError("ZIP file is empty")
                    inner_filename = zf.namelist()[0]
                    inner_7z_path = os.path.join(parent_dir, inner_filename)
                    zf.extract(inner_filename, parent_dir)
                print(" ✓ Done")

                def extract_7z():
                    with py7zr.SevenZipFile(inner_7z_path, mode='r', password='1111') as z:
                        z.extractall(path=parent_dir)
                if not run_python_func_with_spinner(extract_7z, "Step 2: Extracting 7Z"): continue

            target_dir_name = os.path.splitext(os.path.basename(filename).replace(".z删ip", ""))[0]
            target_dir_path = os.path.join(parent_dir, target_dir_name)
            print(f"  -> Step 3: Check and fix directory structure...", end='')
            nested_dir_path = os.path.join(target_dir_path, target_dir_name)
            if os.path.isdir(nested_dir_path):
                print(" ✓ Redundancy detected, starting fix...")
                for item in os.listdir(nested_dir_path): shutil.move(os.path.join(nested_dir_path, item), target_dir_path)
                os.rmdir(nested_dir_path); print("     -> Fix completed.")
            else: print(" ✓ Structure normal.")

        except Exception as e:
            print(f" ❌ Processing failed\nError: {e}")
        finally:
            if temp_zip_path and os.path.exists(temp_zip_path): os.remove(temp_zip_path)
            if inner_7z_path and os.path.exists(inner_7z_path):
                print(f"  -> Step 4: Clean up temporary files...", end=''); os.remove(inner_7z_path); print(" ✓ Done")

    print("\n--- All decryption and recovery tasks completed ---")

def print_final_speedup_info(missing_commands):
    """Before exiting, print platform-specific performance improvement suggestions."""
    if not missing_commands:
        return

    print("\n\n=====================================================")
    print("            🚀 Performance Improvement Suggestions 🚀")
    print("-----------------------------------------------------")
    print("Detected that you are running in compatibility mode. To achieve the fastest")
    print("compression/decompression speed, it is recommended to install the following missing native CLI tools:")
    
    if sys.platform == "darwin":  # macOS
        print("\n[For macOS]")
        if '7z' in missing_commands:
            print("  - 7z:  run `brew install p7zip` in Terminal")
        if 'zip' in missing_commands or 'unzip' in missing_commands:
            print("  - zip/unzip: run `brew install zip`")
    
    elif sys.platform == "win32": # Windows
        print("\n[For Windows]")
        if '7z' in missing_commands:
            print("  - 7z:  download and install from https://www.7-zip.org")
        if 'zip' in missing_commands or 'unzip' in missing_commands:
            print("  - zip/unzip: install via winget or scoop (e.g., `winget install 7zip.7zip`)")

    elif sys.platform.startswith("linux"): # Linux
        print("\n[For Linux]")
        # Check for package manager
        if shutil.which('apt-get'):
            if '7z' in missing_commands:
                print("  - 7z:  run `sudo apt-get install p7zip-full`")
            if 'zip' in missing_commands:
                print("  - zip: run `sudo apt-get install zip`")
            if 'unzip' in missing_commands:
                print("  - unzip: run `sudo apt-get install unzip`")
        elif shutil.which('yum'):
            if '7z' in missing_commands:
                print("  - 7z:  run `sudo yum install p7zip p7zip-plugins`")
            if 'zip' in missing_commands or 'unzip' in missing_commands:
                print("  - zip/unzip: run `sudo yum install zip unzip`")
        else:
            print("  - Use your distribution's package manager to install 'p7zip', 'zip', 'unzip'")
            
    print("\nAfter installation, the tool will automatically switch to high-speed mode next run.")
    print("=====================================================")


def main():
    """Main entry function"""
    print("====================================================="); print("=          Folder Encryption Packing & Decryption Recovery Tool          ="); print("=====================================================")
    
    missing_commands = []
    use_native = NATIVE_7Z_PATH and NATIVE_ZIP_PATH and NATIVE_UNZIP_PATH
    
    if use_native:
        print("\n[Mode] Native 7z/zip commands detected; running in high-speed mode.")
    else:
        print("\n[Mode] Missing some or all native commands; running in pure Python compatibility mode (slower).")
        if not PYTHON_LIBS_AVAILABLE:
            print("\nError: The 'py7zr' library required for pure Python mode is not installed.")
            print("Please install it first via 'pip install py7zr'.")
            sys.exit(1)
        
        if not NATIVE_7Z_PATH: missing_commands.append('7z')
        if not NATIVE_ZIP_PATH: missing_commands.append('zip')
        if not NATIVE_UNZIP_PATH: missing_commands.append('unzip')

    try:
        print("\n 1. Encrypt & Pack (files/folders -> .z删ip) [preserve source files]")
        print(" 2. Decrypt & Restore (.z删ip -> folder)")
        print("----------"); print(" 0. Exit")
        mode = input("\nChoose operation mode: ").strip()
        if mode in ['1', '2']:
            default_path = load_default_path_from_settings()
            prompt_message = f"\nEnter working directory path (press Enter to use default: {default_path}): "
            parent_dir = input(prompt_message).strip() or default_path
            if not os.path.isdir(parent_dir): sys.exit(f"\nError: Directory '{parent_dir}' does not exist.")
            if mode == '1': encode_items_in_dir(parent_dir)
            elif mode == '2': decode_files_in_dir(parent_dir)
        elif mode == '0':
            pass # Allow to proceed to finally block
        else:
            print("\nError: Invalid selection.")
    
    finally:
        print_final_speedup_info(missing_commands)
        sys.exit("Operation complete, program exited.")


if __name__ == "__main__":
    main()