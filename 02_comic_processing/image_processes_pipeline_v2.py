import os
import shutil
from PIL import Image, ImageFile
import natsort
import sys
from collections import Counter
import math
import traceback
import json

# --- Global Settings ---
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

MERGED_LONG_IMAGE_SUBDIR_NAME = "merged_long_img"
SPLIT_IMAGES_SUBDIR_NAME = "split_by_solid_band"
SUCCESS_MOVE_SUBDIR_NAME = "IMG"  # Successfully processed folders will be moved to this directory

LONG_IMAGE_FILENAME_BASE = "stitched_long_strip"
IMAGE_EXTENSIONS_FOR_MERGE = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif')

MIN_SOLID_COLOR_BAND_HEIGHT = 50
COLOR_MATCH_TOLERANCE = 45

# Common background colors for Korean webtoons (extended)
SPLIT_BAND_COLORS_RGB = [
    # Base colors
    (255, 255, 255),  # Pure white
    (0, 0, 0),        # Pure black
    
    # Light backgrounds common in Korean webtoons
    (248, 248, 248),  # Light gray-white
    (240, 240, 240),  # Gray-white
    (250, 250, 250),  # Near white
    (245, 245, 245),  # Pale gray
    (252, 252, 252),  # Very light gray
    (242, 242, 242),  # Light gray
    (238, 238, 238),  # Medium-light gray
    (235, 235, 235),  # Silver gray
    (230, 230, 230),  # Light silver gray
    (225, 225, 225),  # Medium silver gray
    (220, 220, 220),  # Dark silver gray
    (215, 215, 215),  # Light steel gray
    (210, 210, 210),  # Steel gray
    (205, 205, 205),  # Dark steel gray
    (200, 200, 200),  # Medium gray
    
    # Beige/cream backgrounds
    (255, 253, 250),  # Snow white
    (253, 245, 230),  # Antique white
    (250, 240, 230),  # Linen
    (255, 248, 220),  # Cornsilk
    (255, 250, 240),  # Floral white
    (253, 245, 230),  # Old lace
    (245, 245, 220),  # Beige
    (255, 228, 196),  # Bisque
    
    # Light pink backgrounds
    (255, 240, 245),  # Lavender blush
    (255, 228, 225),  # Misty rose
    (255, 218, 185),  # Peach puff
    (255, 239, 213),  # Papaya whip
    (255, 235, 205),  # Blanched almond
    
    # Light blue backgrounds
    (240, 248, 255),  # Alice blue
    (230, 230, 250),  # Lavender
    (248, 248, 255),  # Ghost white
    (245, 245, 245),  # White smoke
    (220, 220, 220),  # Light gray
    
    # Light green/blue backgrounds
    (240, 255, 240),  # Honeydew
    (245, 255, 250),  # Mint cream
    (240, 255, 255),  # Azure
    
    # Dark backgrounds
    (195, 195, 195),  # Dark medium gray
    (190, 190, 190),  # Dim gray
    (185, 185, 185),  # Dark dim gray
    (180, 180, 180),  # Gray
    (175, 175, 175),  # Dark gray
    (170, 170, 170),  # Deep dim gray
    (165, 165, 165),  # Charcoal gray
    (160, 160, 160),  # Dark charcoal gray
    (155, 155, 155),  # Dim charcoal gray
    (150, 150, 150),  # Medium charcoal gray
    (145, 145, 145),  # Dark medium charcoal gray
    (140, 140, 140),  # Dim medium charcoal gray
    (135, 135, 135),  # Dark dim charcoal gray
    (130, 130, 130),  # Very dark charcoal gray
    (125, 125, 125),  # Deep very dark charcoal gray
    (120, 120, 120),  # Dim very dark charcoal gray
    (115, 115, 115),  # Dark dim very dark charcoal gray
    (110, 110, 110),  # Extremely dark charcoal gray
    (105, 105, 105),  # Deep extremely dark charcoal gray
    (100, 100, 100),  # Dim extremely dark charcoal gray
    (95, 95, 95),     # Dark extremely dark charcoal gray
    (90, 90, 90),     # Very dark deep charcoal gray
    (85, 85, 85),     # Deep very dark deep charcoal gray
    (80, 80, 80),     # Dim very dark deep charcoal gray
    (75, 75, 75),     # Dark very dark deep charcoal gray
    (70, 70, 70),     # Extremely dark deep charcoal gray
    (65, 65, 65),     # Deep extremely dark deep charcoal gray
    (60, 60, 60),     # Dim extremely dark deep charcoal gray
    (55, 55, 55),     # Dark dim extremely dark deep charcoal gray
    (50, 50, 50),     # Very dark dim extremely dark charcoal gray
    (45, 45, 45),     # Deep very dark dim extremely dark charcoal gray
    (40, 40, 40),     # Dim very dark deep extremely dark charcoal gray
    (35, 35, 35),     # Dark very dark deep extremely dark charcoal gray
    (30, 30, 30),     # Extremely dark very deep charcoal gray
    (25, 25, 25),     # Deep extremely dark very deep charcoal gray
    (20, 20, 20),     # Dim extremely dark very deep charcoal gray
    (15, 15, 15),     # Dark dim extremely dark very deep charcoal gray
    (10, 10, 10),     # Very dark dim extremely dark very deep charcoal gray
    (5, 5, 5),        # Nearly black
]

PDF_TARGET_PAGE_WIDTH_PIXELS = 1500
PDF_IMAGE_JPEG_QUALITY = 85
PDF_DPI = 300
# --- End of Global Settings ---


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """
    Print a progress bar in the terminal.
    """
    if total == 0:
        percent_str = "0.0%"
        filled_length = 0
    else:
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        percent_str = f"{percent}%"
        filled_length = int(length * iteration // total)

    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent_str} {suffix}')
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')
        sys.stdout.flush()


def merge_to_long_image(source_project_dir, output_long_image_dir, long_image_filename_only):
    """
    Recursively find all images in the source project directory and its subdirectories,
    perform natural sorting, and vertically merge into a PNG long image.
    """
    print(f"\n  --- Step 1: Merge all images in project '{os.path.basename(source_project_dir)}' into a long image ---")
    if not os.path.isdir(source_project_dir):
        print(f"    Error: Source project directory '{source_project_dir}' not found.")
        return None

    os.makedirs(output_long_image_dir, exist_ok=True)
    output_long_image_path = os.path.join(output_long_image_dir, long_image_filename_only)

    print(f"    ... Recursively scanning '{os.path.basename(source_project_dir)}' and all subfolders for images ...")
    image_filepaths = []
    try:
        for dirpath, _, filenames in os.walk(source_project_dir):
            # 确保不扫描脚本自己创建的中间文件夹
            if MERGED_LONG_IMAGE_SUBDIR_NAME in dirpath or SPLIT_IMAGES_SUBDIR_NAME in dirpath:
                continue
            
            for filename in filenames:
                if filename.lower().endswith(IMAGE_EXTENSIONS_FOR_MERGE) and not filename.startswith('.'):
                    image_filepaths.append(os.path.join(dirpath, filename))
    except Exception as e:
        print(f"    Error: An error occurred while scanning directory '{source_project_dir}': {e}")
        return None
        
    if not image_filepaths:
        print(f"    No eligible images found in '{os.path.basename(source_project_dir)}' or its subdirectories.")
        return None

    # Perform natural sorting on collected full paths
    sorted_image_filepaths = natsort.natsorted(image_filepaths)

    images_data = []
    total_calculated_height = 0
    max_calculated_width = 0

    total_files_to_analyze = len(sorted_image_filepaths)
    if total_files_to_analyze > 0:
        print_progress_bar(0, total_files_to_analyze, prefix='    Analyzing image dimensions:', suffix='Done', length=40)
    
    for i, filepath in enumerate(sorted_image_filepaths):
        try:
            with Image.open(filepath) as img:
                images_data.append({
                    "path": filepath,
                    "width": img.width,
                    "height": img.height
                })
                total_calculated_height += img.height
                if img.width > max_calculated_width:
                    max_calculated_width = img.width
        except Exception as e:
            print(f"\n    Warning: Failed to open or read image '{os.path.basename(filepath)}': {e}. Skipped.")
            continue
        if total_files_to_analyze > 0:
            print_progress_bar(i + 1, total_files_to_analyze, prefix='    Analyzing image dimensions:', suffix='Done', length=40)

    if not images_data:
        print("    No valid images available for merging.")
        return None

    if max_calculated_width == 0 or total_calculated_height == 0:
        print(f"    Computed canvas size is zero ({max_calculated_width}x{total_calculated_height}); cannot create long image.")
        return None

    merged_canvas = Image.new('RGBA', (max_calculated_width, total_calculated_height), (0, 0, 0, 0))
    current_y_offset = 0

    total_files_to_paste = len(images_data)
    if total_files_to_paste > 0:
        print_progress_bar(0, total_files_to_paste, prefix='    Pasting images:    ', suffix='Done', length=40)
    for i, item_info in enumerate(images_data):
        try:
            with Image.open(item_info["path"]) as img:
                img_to_paste = img.convert("RGBA")
                x_offset = (max_calculated_width - img_to_paste.width) // 2
                merged_canvas.paste(img_to_paste, (x_offset, current_y_offset), img_to_paste if img_to_paste.mode == 'RGBA' else None)
                current_y_offset += item_info["height"]
        except Exception as e:
            print(f"\n    Warning: Failed to paste image '{item_info['path']}': {e}.")
            pass
        if total_files_to_paste > 0:
            print_progress_bar(i + 1, total_files_to_paste, prefix='    Pasting images:    ', suffix='Done', length=40)

    try:
        merged_canvas.save(output_long_image_path, format='PNG')
        print(f"    Successfully merged images to: {output_long_image_path}")
        return output_long_image_path
    except Exception as e:
        print(f"    Error: Failed to save merged long image: {e}")
        return None


# Note: The original detect_and_add_background_colors function has been removed.
# We now directly use preset common Korean webtoon background colors to improve speed and efficiency.

def are_colors_close(color1, color2, tolerance):
    """Check whether two RGB colors are close based on Euclidean distance."""
    if tolerance == 0:
        return color1 == color2
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    distance = math.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2)
    return distance <= tolerance

def is_solid_color_row(pixels, y, width, solid_colors_list, tolerance):
    """Check if a given row is a solid color band within a tolerance."""
    if width == 0:
        return False

    first_pixel_rgb = pixels[0, y][:3]
    
    base_color_match = None
    for base_color in solid_colors_list:
        if are_colors_close(first_pixel_rgb, base_color, tolerance):
            base_color_match = first_pixel_rgb
            break
            
    if base_color_match is None:
        return False
        
    for x in range(1, width):
        if not are_colors_close(pixels[x, y][:3], base_color_match, tolerance):
            return False
            
    return True

def split_long_image(long_image_path, output_split_dir, min_solid_band_height, band_colors_list, tolerance):
    """Split long images based on finding content rows after sufficiently tall solid color bands."""
    print(f"\n  --- Step 2: Split long image '{os.path.basename(long_image_path)}' by solid color bands ---")
    if not os.path.isfile(long_image_path):
        print(f"    Error: Long image path '{long_image_path}' not found.")
        return []

    os.makedirs(output_split_dir, exist_ok=True)
    split_image_paths = []

    try:
        if min_solid_band_height < 1: min_solid_band_height = 1

        img = Image.open(long_image_path).convert("RGBA")
        pixels = img.load()
        img_width, img_height = img.size

        if img_height == 0 or img_width == 0:
            print(f"    Image '{os.path.basename(long_image_path)}' has zero dimensions; cannot split.")
            return []

        original_basename, _ = os.path.splitext(os.path.basename(long_image_path))
        part_index = 1
        current_segment_start_y = 0
        solid_band_after_last_content_start_y = -1

        print_progress_bar(0, img_height, prefix='    Scanning long image:    ', suffix='Done', length=40)

        for y in range(img_height):
            print_progress_bar(y + 1, img_height, prefix='    Scanning long image:    ', suffix=f'Row {y+1}/{img_height}', length=40)

            is_solid = is_solid_color_row(pixels, y, img_width, band_colors_list, tolerance)

            if not is_solid:  # This is a "content" row
                if solid_band_after_last_content_start_y != -1:
                    solid_band_height = y - solid_band_after_last_content_start_y
                    if solid_band_height >= min_solid_band_height:
                        cut_point_y = solid_band_after_last_content_start_y + (solid_band_height // 2)
                        if cut_point_y > current_segment_start_y:
                            segment = img.crop((0, current_segment_start_y, img_width, cut_point_y))
                            output_filename = f"{original_basename}_split_part_{part_index}.png"
                            output_filepath = os.path.join(output_split_dir, output_filename)
                            try:
                                segment.save(output_filepath, "PNG")
                                split_image_paths.append(output_filepath)
                                part_index += 1
                            except Exception as e_save:
                                print(f"      保存分割片段 '{output_filename}' 失败: {e_save}")
                        current_segment_start_y = cut_point_y
                solid_band_after_last_content_start_y = -1
            else:  # This is a "solid" row
                if solid_band_after_last_content_start_y == -1:
                    solid_band_after_last_content_start_y = y

        if current_segment_start_y < img_height:
            segment = img.crop((0, current_segment_start_y, img_width, img_height))
            if segment.height > 10:  # Avoid saving very small slices
                output_filename = f"{original_basename}_split_part_{part_index}.png"
                output_filepath = os.path.join(output_split_dir, output_filename)
                try:
                    segment.save(output_filepath, "PNG")
                    split_image_paths.append(output_filepath)
                except Exception as e_save:
                    print(f"      Failed to save the last split segment '{output_filename}': {e_save}")

        if not split_image_paths and img_height > 0:
            print(f"    Failed to split '{os.path.basename(long_image_path)}' based on the specified solid bands.")
            print(f"    The original merged long image will be used for the next step.")
            shutil.copy2(long_image_path, os.path.join(output_split_dir, os.path.basename(long_image_path)))
            return [os.path.join(output_split_dir, os.path.basename(long_image_path))]

    except Exception as e:
        print(f"    Error while splitting image '{os.path.basename(long_image_path)}': {e}")
        traceback.print_exc()

    return natsort.natsorted(split_image_paths)


def _merge_image_list_for_repack(image_paths, output_path):
    """An internal helper function specifically for repacking."""
    if not image_paths:
        return False
    
    images_data = []
    total_height = 0
    max_width = 0
    for path in image_paths:
        try:
            with Image.open(path) as img:
                images_data.append({"path": path, "width": img.width, "height": img.height})
                total_height += img.height
                if img.width > max_width:
                    max_width = img.width
        except Exception:
            continue
            
    if not images_data: return False

    merged_canvas = Image.new('RGBA', (max_width, total_height))
    current_y = 0
    for item in images_data:
        with Image.open(item["path"]) as img:
            img_to_paste = img.convert("RGBA")
            x_offset = (max_width - item["width"]) // 2
            merged_canvas.paste(img_to_paste, (x_offset, current_y), img_to_paste)
            current_y += item["height"]
            
    merged_canvas.save(output_path, "PNG")
    return True


def repack_split_images(split_image_paths, output_dir, base_filename, max_size_mb=8):
    """
    Repack split images by size.
    - Upper limit per merged image block is max_size_mb.
    - If a single image exceeds the limit, it is retained as-is and not merged.
    """
    print(f"\n  --- Step 2.5: Repack image blocks (target size: < {max_size_mb}MB) ---")
    if not split_image_paths:
        print("    No images available for repacking.")
        return []

    max_size_bytes = max_size_mb * 1024 * 1024
    
    repacked_paths = []
    current_bucket = []
    current_bucket_size = 0
    repack_index = 1
    
    total_files = len(split_image_paths)
    print_progress_bar(0, total_files, prefix='    Processing image blocks: ', suffix='Start', length=40)

    for i, img_path in enumerate(split_image_paths):
        if not os.path.exists(img_path): continue
        
        file_size = os.path.getsize(img_path)
        
        # 情况1: 单个文件已经超过上限
        if file_size > max_size_bytes:
            # 首先，打包当前桶中已有的图片
            if current_bucket:
                output_filename = f"{base_filename}_repacked_{repack_index}.png"
                output_path = os.path.join(output_dir, output_filename)
                if _merge_image_list_for_repack(current_bucket, output_path):
                    repacked_paths.append(output_path)
                    repack_index += 1
                current_bucket = []
                current_bucket_size = 0
            
            # 然后，直接复制这个过大的文件
            output_filename_oversized = f"{base_filename}_repacked_{repack_index}.png"
            output_path_oversized = os.path.join(output_dir, output_filename_oversized)
            shutil.copy2(img_path, output_path_oversized)
            repacked_paths.append(output_path_oversized)
            repack_index += 1
            print_progress_bar(i + 1, total_files, prefix='    Processing image blocks: ', suffix=f'{repack_index-1} bundle(s) complete', length=40)
            continue # 处理下一个文件

        # 情况2: 将当前文件加入桶中会超出上限
        if current_bucket and (current_bucket_size + file_size) > max_size_bytes:
            # 先打包当前的桶
            output_filename = f"{base_filename}_repacked_{repack_index}.png"
            output_path = os.path.join(output_dir, output_filename)
            if _merge_image_list_for_repack(current_bucket, output_path):
                repacked_paths.append(output_path)
                repack_index += 1
            
            # 用当前文件开始一个新的桶
            current_bucket = [img_path]
            current_bucket_size = file_size
        else:
            # 情况3: 桶还有空间，加入当前文件
            current_bucket.append(img_path)
            current_bucket_size += file_size
        
        print_progress_bar(i + 1, total_files, prefix='    Processing image blocks: ', suffix=f'{repack_index-1} bundle(s) complete', length=40)

    # 处理循环结束后所有剩余在桶中的图片
    if current_bucket:
        output_filename = f"{base_filename}_repacked_{repack_index}.png"
        output_path = os.path.join(output_dir, output_filename)
        if _merge_image_list_for_repack(current_bucket, output_path):
            repacked_paths.append(output_path)
    
    print_progress_bar(total_files, total_files, prefix='    Processing image blocks: ', suffix='All done', length=40)
    print(f"    Repack complete. Generated {len(repacked_paths)} new image block(s).")

    # 清理掉原始的、未打包的分割图片
    print("    ... Cleaning up original split files ...")
    for path in split_image_paths:
        try:
            os.remove(path)
        except OSError as e:
            print(f"      Unable to delete original file {os.path.basename(path)}: {e}")

    return natsort.natsorted(repacked_paths)

def create_pdf_from_images(image_paths_list, output_pdf_dir, pdf_filename_only,
                           target_page_width_px, image_jpeg_quality, pdf_target_dpi):
    """Create a PDF file from a list of image paths."""
    print(f"\n  --- Step 3: Create PDF '{pdf_filename_only}' from image blocks ---")
    if not image_paths_list:
        print("    No image blocks available to create a PDF.")
        return None

    pdf_full_path = os.path.join(output_pdf_dir, pdf_filename_only)
    
    processed_pil_images = []
    
    total_images_for_pdf = len(image_paths_list)
    if total_images_for_pdf > 0:
        print_progress_bar(0, total_images_for_pdf, prefix='    处理PDF图片:', suffix='完成', length=40)

    for i, image_path in enumerate(image_paths_list):
        try:
            with Image.open(image_path) as img:
                img_to_process = img
                if img_to_process.mode not in ['RGB', 'L']:
                    background = Image.new("RGB", img_to_process.size, (255, 255, 255))
                    try:
                        mask = img_to_process.getchannel('A')
                        background.paste(img_to_process, mask=mask)
                    except (ValueError, KeyError):
                        background.paste(img_to_process.convert("RGB"))
                    img_to_process = background
                elif img_to_process.mode == 'L':
                    img_to_process = img_to_process.convert('RGB')

                original_width, original_height = img_to_process.size
                if original_width == 0 or original_height == 0:
                    print(f"    Warning: Image '{os.path.basename(image_path)}' has zero dimensions; skipped.")
                    if total_images_for_pdf > 0: print_progress_bar(i + 1, total_images_for_pdf, prefix='    处理PDF图片:', suffix='完成', length=40)
                    continue
                
                if original_width > target_page_width_px:
                    ratio = target_page_width_px / original_width
                    new_height = int(original_height * ratio)
                    if new_height <=0: new_height = 1
                    img_resized = img_to_process.resize((target_page_width_px, new_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img_to_process.copy()

                processed_pil_images.append(img_resized)

        except Exception as e:
            print(f"\n    Warning: Failed to process PDF image '{os.path.basename(image_path)}': {e}. Skipped.")
            pass
        if total_images_for_pdf > 0:
            print_progress_bar(i + 1, total_images_for_pdf, prefix='    Processing PDF images:', suffix='Done', length=40)

    if not processed_pil_images:
        print("    没有图片被成功处理以包含在PDF中。")
        return None

    try:
        first_image_to_save = processed_pil_images[0]
        images_to_append = processed_pil_images[1:]

        first_image_to_save.save(
            pdf_full_path,
            save_all=True,
            append_images=images_to_append,
            resolution=float(pdf_target_dpi),
            quality=image_jpeg_quality,
            optimize=True
        )
        print(f"    Successfully created PDF: {pdf_full_path}")
        return pdf_full_path
    except Exception as e:
        print(f"    Failed to save PDF: {e}")
        return None
    finally:
        for img_obj in processed_pil_images:
            try:
                img_obj.close()
            except Exception:
                pass


def cleanup_intermediate_dirs(long_img_dir, split_img_dir):
    """Clean specified intermediate file directories."""
    print(f"\n  --- Step 4: Clean up intermediate files ---")
    for dir_to_remove, dir_name_for_log in [(long_img_dir, "Long image merge"), (split_img_dir, "Image split and repack")]:
        if os.path.isdir(dir_to_remove):
            try:
                shutil.rmtree(dir_to_remove)
                print(f"    Deleted intermediate '{dir_name_for_log}' folder: {dir_to_remove}")
            except Exception as e:
                print(f"    Failed to delete folder '{dir_to_remove}': {e}")


if __name__ == "__main__":
    print("Automated Image Batch Processing Workflow (V3.6 - Centralized PDF output folder)")
    print("Workflow: 1.Merge -> 2.Split -> 2.5.Repack -> 3.Create PDF -> 4.Cleanup -> 5.Move successful items")
    print("-" * 70)
    
    def load_default_path_from_settings():
        """Read default work directory from the shared settings file."""
        try:
            # Navigate up two levels to find the project root, then locate settings.json
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            # Treat empty or null default_work_dir as invalid
            default_dir = settings.get("default_work_dir")
            return default_dir if default_dir else "."
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to read settings.json ({e}). Using fallback path.")
            # Provide a generic fallback path if settings cannot be read
            return os.path.join(os.path.expanduser("~"), "Downloads")
    
    default_root_dir_name = load_default_path_from_settings()

    root_input_dir = ""
    while True:
        prompt_message = (
            f"Please enter the [root directory] path containing one or more project subfolders.\n"
            f"The script will recursively process all images in each project subfolder.\n"
            f"(Press Enter to use the default path: '{default_root_dir_name}'): "
        )
        user_provided_path = input(prompt_message).strip()
        current_path_to_check = user_provided_path if user_provided_path else default_root_dir_name
        if not user_provided_path:
            print(f"Using default path: {current_path_to_check}")

        abs_path_to_check = os.path.abspath(current_path_to_check)
        if os.path.isdir(abs_path_to_check):
            root_input_dir = abs_path_to_check
            print(f"Selected root processing directory: {root_input_dir}")
            break
        else:
            print(f"Error: Path '{abs_path_to_check}' is not a valid directory or does not exist.")

    # Create a unique PDF output folder based on the root directory name
    root_dir_basename = os.path.basename(os.path.abspath(root_input_dir))
    overall_pdf_output_dir = os.path.join(root_input_dir, f"{root_dir_basename}_pdfs")
    os.makedirs(overall_pdf_output_dir, exist_ok=True)
    
    # Create a folder to store successfully processed projects
    success_move_target_dir = os.path.join(root_input_dir, SUCCESS_MOVE_SUBDIR_NAME)
    os.makedirs(success_move_target_dir, exist_ok=True)

    # Scan project subfolders to process, excluding script management folders
    subdirectories = [d for d in os.listdir(root_input_dir)
                      if os.path.isdir(os.path.join(root_input_dir, d)) and \
                         d != SUCCESS_MOVE_SUBDIR_NAME and \
                         d != os.path.basename(overall_pdf_output_dir) and \
                         not d.startswith('.')]

    if not subdirectories:
        print(f"\nNo processable project subfolders found in root directory '{root_input_dir}'.")
        sys.exit()

    sorted_subdirectories = natsort.natsorted(subdirectories)
    print(f"\nWill process the following {len(sorted_subdirectories)} project folders in order: {', '.join(sorted_subdirectories)}")

    total_subdirs_to_process = len(sorted_subdirectories)
    failed_subdirs_list = []

    for i, subdir_name in enumerate(sorted_subdirectories):
        print_progress_bar(i, total_subdirs_to_process, prefix="Total progress:", suffix=f'{subdir_name}', length=40)
        print(f"\n\n{'='*10} Starting project folder: {subdir_name} ({i+1}/{total_subdirs_to_process}) {'='*10}")
        
        current_processing_subdir = os.path.join(root_input_dir, subdir_name)

        # Intermediate files are stored inside the project folder being processed
        path_long_image_output_dir_current = os.path.join(current_processing_subdir, MERGED_LONG_IMAGE_SUBDIR_NAME)
        path_split_images_output_dir_current = os.path.join(current_processing_subdir, SPLIT_IMAGES_SUBDIR_NAME)
        current_long_image_filename = f"{subdir_name}_{LONG_IMAGE_FILENAME_BASE}.png"

        # Call the modified merge function, which recursively scans current_processing_subdir
        created_long_image_path = merge_to_long_image(
            current_processing_subdir,
            path_long_image_output_dir_current,
            current_long_image_filename
        )

        pdf_created_for_this_subdir = False
        if created_long_image_path:
            # Directly use preset common Korean webtoon background colors to improve speed and efficiency
            print(f"    🎨 Using preset common Korean webtoon background colors to improve speed and efficiency...")
            
            split_segment_paths = split_long_image(
                created_long_image_path,
                path_split_images_output_dir_current,
                MIN_SOLID_COLOR_BAND_HEIGHT,
                SPLIT_BAND_COLORS_RGB,
                COLOR_MATCH_TOLERANCE
            )

            repacked_final_paths = repack_split_images(
                split_segment_paths,
                path_split_images_output_dir_current,
                base_filename=subdir_name,
                max_size_mb=5
            )

            if repacked_final_paths:
                dynamic_pdf_filename_for_subdir = subdir_name + ".pdf"
                
                # 始终使用唯一的、总体的PDF输出目录
                created_pdf_path = create_pdf_from_images(
                    repacked_final_paths,
                    overall_pdf_output_dir, 
                    dynamic_pdf_filename_for_subdir,
                    PDF_TARGET_PAGE_WIDTH_PIXELS,
                    PDF_IMAGE_JPEG_QUALITY,
                    PDF_DPI
                )
                if created_pdf_path:
                    pdf_created_for_this_subdir = True

        if pdf_created_for_this_subdir:
            cleanup_intermediate_dirs(path_long_image_output_dir_current, path_split_images_output_dir_current)
            
            print(f"\n  --- Step 5: Move successfully processed project folder ---")
            source_folder_to_move = current_processing_subdir
            destination_parent_folder = success_move_target_dir
            
            try:
                print(f"    Preparing to move '{os.path.basename(source_folder_to_move)}' into folder '{os.path.basename(destination_parent_folder)}'...")
                shutil.move(source_folder_to_move, destination_parent_folder)
                moved_path = os.path.join(destination_parent_folder, os.path.basename(source_folder_to_move))
                print(f"    Successfully moved folder to: {moved_path}")
            except Exception as e:
                print(f"    Error: Failed to move folder '{os.path.basename(source_folder_to_move)}': {e}")
                if subdir_name not in failed_subdirs_list:
                    failed_subdirs_list.append(f"{subdir_name} (Move failed)")
            
        else:
            print(f"  Project folder '{subdir_name}' did not successfully generate a PDF. Intermediate files and original folder retained.")
            failed_subdirs_list.append(subdir_name)

        print(f"{'='*10} Project folder '{subdir_name}' processing complete {'='*10}")
        print_progress_bar(i + 1, total_subdirs_to_process, prefix="Total progress:", suffix='Done', length=40)

    print("\n" + "=" * 70)
    print("[Task Summary Report]")
    print("-" * 70)
    
    success_count = total_subdirs_to_process - len(failed_subdirs_list)
    
    print(f"Total projects processed (top-level subfolders): {total_subdirs_to_process}")
    print(f"  - ✅ Success: {success_count}")
    print(f"  - ❌ Failed: {len(failed_subdirs_list)}")
    
    if failed_subdirs_list:
        print("\nFailed projects (retained in place):")
        for failed_dir in failed_subdirs_list:
            print(f"  - {failed_dir}")
    
    print("-" * 70)
    print(f"All successfully generated PDF files (if any) are saved in: {overall_pdf_output_dir}")
    print(f"All successfully processed original project folders (if any) have been moved to: {success_move_target_dir}")
    print("Script execution complete.")