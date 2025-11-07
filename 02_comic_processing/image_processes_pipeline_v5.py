import os
import shutil
from PIL import Image, ImageFile
import natsort
import sys
from collections import Counter
import math
import traceback
import json
import time

try:
    import numpy as np
except ImportError:
    print("Error: This script requires the numpy library. Please install it with 'pip install numpy'.")
    sys.exit(1)

# --- Global Settings ---
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

# --- Directory and Filename Settings ---
MERGED_LONG_IMAGE_SUBDIR_NAME = "merged_long_img"
SPLIT_IMAGES_SUBDIR_NAME = "split_by_solid_band"
SUCCESS_MOVE_SUBDIR_NAME = "IMG"  # Successfully processed folders will be moved to this directory
LONG_IMAGE_FILENAME_BASE = "stitched_long_strip"
IMAGE_EXTENSIONS_FOR_MERGE = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif')

# --- V2 Split Configuration ---
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

# --- V4 Split Configuration ---
QUANTIZATION_FACTOR = 32
MAX_UNIQUE_COLORS_IN_BG = 5
MIN_SOLID_COLOR_BAND_HEIGHT_V4 = 30
EDGE_MARGIN_PERCENT = 0.10

# --- Repack and PDF Output Settings ---
MAX_REPACKED_FILESIZE_MB = 8
MAX_REPACKED_PAGE_HEIGHT_PX = 30000
PDF_TARGET_PAGE_WIDTH_PIXELS = 1500
PDF_IMAGE_JPEG_QUALITY = 85
PDF_DPI = 300
# --- End of Settings ---


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """Print a progress bar in the terminal."""
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


def merge_to_long_image(source_project_dir, output_long_image_dir, long_image_filename_only, target_width=None):
    """Vertically merge all images (including subdirectories) from the source directory into a long image."""
    print(f"\n  --- Step 1: Merge all images in project '{os.path.basename(source_project_dir)}' to create a long image ---")
    if not os.path.isdir(source_project_dir):
        print(f"    Error: Source project directory '{source_project_dir}' not found.")
        return None

    os.makedirs(output_long_image_dir, exist_ok=True)
    output_long_image_path = os.path.join(output_long_image_dir, long_image_filename_only)

    print(f"    ... Recursively scanning '{os.path.basename(source_project_dir)}' and all subfolders for images ...")
    image_filepaths = []
    try:
        for dirpath, _, filenames in os.walk(source_project_dir):
            # Ensure we do not scan intermediate folders created by the script itself
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
                if target_width and img.width != target_width:
                    new_height = int(img.height * (target_width / img.width))
                    images_data.append({
                        "path": filepath,
                        "width": target_width,
                        "height": new_height,
                        "original_width": img.width,
                        "original_height": img.height
                    })
                    total_calculated_height += new_height
                    max_calculated_width = target_width
                else:
                    images_data.append({
                        "path": filepath,
                        "width": img.width,
                        "height": img.height,
                        "original_width": img.width,
                        "original_height": img.height
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

    merged_canvas = Image.new('RGB', (max_calculated_width, total_calculated_height), (255, 255, 255))
    current_y_offset = 0

    total_files_to_paste = len(images_data)
    if total_files_to_paste > 0:
        print_progress_bar(0, total_files_to_paste, prefix='    Pasting images:    ', suffix='Done', length=40)
    for i, item_info in enumerate(images_data):
        try:
            with Image.open(item_info["path"]) as img:
                img_rgb = img.convert("RGB")
                if target_width and img_rgb.width != target_width:
                    img_to_paste = img_rgb.resize((target_width, item_info['height']), Image.Resampling.LANCZOS)
                else:
                    img_to_paste = img_rgb
                
                if target_width:
                    merged_canvas.paste(img_to_paste, (0, current_y_offset))
                else:
                    x_offset = (max_calculated_width - img_to_paste.width) // 2
                    merged_canvas.paste(img_to_paste, (x_offset, current_y_offset))
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


# --- V2 Split-related Functions ---


def are_colors_close(color1, color2, tolerance):
    """Check whether two RGB colors are close based on Euclidean distance."""
    if tolerance == 0:
        return color1 == color2
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    distance = math.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2)
    return distance <= tolerance


def is_solid_color_row(pixels, y, width, solid_colors_list, tolerance):
    """Check if the given row is a solid color band within a tolerance."""
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


def split_long_image_v2(long_image_path, output_split_dir, min_solid_band_height, band_colors_list, tolerance):
    """V2 split method: Split long images by finding content rows after sufficiently tall solid-color bands."""
    print(f"\n  --- Step 2 (V2 - traditional solid-band analysis): Split long image '{os.path.basename(long_image_path)}' ---")
    if not os.path.isfile(long_image_path):
        print(f"    Error: Long image path '{long_image_path}' not found.")
        return []

    os.makedirs(output_split_dir, exist_ok=True)
    split_image_paths = []

    try:
        if min_solid_band_height < 1: 
            min_solid_band_height = 1

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
                                print(f"      Failed to save split segment '{output_filename}': {e_save}")
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
            print(f"    V2 method failed to split '{os.path.basename(long_image_path)}' based on the specified solid bands.")
            return []

    except Exception as e:
        print(f"    V2 split encountered an error for image '{os.path.basename(long_image_path)}': {e}")
        traceback.print_exc()
        return []

    return natsort.natsorted(split_image_paths)


# --- V4 Split-related Functions ---
def get_dominant_color_numpy(pixels_quantized):
    """[V4 performance core] Use pure NumPy to find the dominant color from quantized pixel blocks."""
    if pixels_quantized.size == 0:
        return None, 0
    pixels_list = pixels_quantized.reshape(-1, 3)
    unique_colors, counts = np.unique(pixels_list, axis=0, return_counts=True)
    num_unique_colors = len(unique_colors)
    if num_unique_colors == 0:
        return None, 0
    dominant_color = tuple(unique_colors[np.argmax(counts)])
    return dominant_color, num_unique_colors


def split_long_image_v4(long_image_path, output_split_dir, quantization_factor, max_unique_colors, min_band_height, edge_margin_percent):
    """V4 split method: Identify and split images via two-stage vectorized analysis for high speed."""
    print(f"\n  --- Step 2 (V4 - two-stage fast analysis): Split long image '{os.path.basename(long_image_path)}' ---")
    start_time = time.time()
    if not os.path.isfile(long_image_path):
        print(f"    Error: Long image path '{long_image_path}' not found.")
        return []

    os.makedirs(output_split_dir, exist_ok=True)
    
    try:
        with Image.open(long_image_path) as img:
            img_rgb = img.convert("RGB")
            img_width, img_height = img_rgb.size
            if img_height < min_band_height * 3:  # If the image is too short, splitting is unnecessary
                print("    Image too short; no need to split.")
                return []

            print(f"    Analyzing an image of {img_width}x{img_height}...")
            print("    [1/3] Color quantization...")
            quantized_array = np.array(img_rgb) // quantization_factor
            
            margin_width = int(img_width * edge_margin_percent)
            center_start, center_end = margin_width, img_width - margin_width

            # --- [V4 Core Optimization 1: Fast candidate screening] ---
            print("    [2/3] Fast screening of candidate rows...")
            candidate_indices = []
            candidate_dominant_colors = {}
            # Still per-row, but only analyze the fastest center region
            for y in range(img_height):
                center_pixels = quantized_array[y, center_start:center_end]
                dominant_color, color_count = get_dominant_color_numpy(center_pixels)
                if color_count <= max_unique_colors and dominant_color is not None:
                    candidate_indices.append(y)
                    candidate_dominant_colors[y] = dominant_color
            
            if not candidate_indices:
                print("    No candidate rows found; V4 method cannot split.")
                return []

            # --- [V4 Core Optimization 2: Precise edge verification] ---
            print(f"    [3/3] Precisely verifying edges across {len(candidate_indices)} candidate rows...")
            row_types = np.full(img_height, 'complex', dtype=object)
            # 只对少数候选行进行耗时的边缘分析
            for y in candidate_indices:
                center_dominant_color = candidate_dominant_colors[y]
                
                # 分析左边缘
                left_pixels = quantized_array[y, :margin_width]
                left_dominant_color, left_color_count = get_dominant_color_numpy(left_pixels)
                if left_color_count > max_unique_colors or left_dominant_color != center_dominant_color:
                    continue

                # 分析右边缘
                right_pixels = quantized_array[y, -margin_width:]
                right_dominant_color, right_color_count = get_dominant_color_numpy(right_pixels)
                if right_color_count > max_unique_colors or right_dominant_color != center_dominant_color:
                    continue
                
                row_types[y] = 'simple'
            
            analysis_duration = time.time() - start_time
            print(f"    Analysis completed in: {analysis_duration:.2f} seconds.")

            # --- 后续的切块与保存逻辑 ---
            blocks, last_y = [], 0
            change_points = np.where(row_types[:-1] != row_types[1:])[0] + 1
            for y_change in change_points:
                blocks.append({'type': row_types[last_y], 'start': last_y, 'end': y_change})
                last_y = y_change
            blocks.append({'type': row_types[last_y], 'start': last_y, 'end': img_height})
            
            original_basename, _ = os.path.splitext(os.path.basename(long_image_path))
            part_index, last_cut_y, cut_found = 1, 0, False
            split_image_paths = []
            
            print(f"    Searching cut points among {len(blocks)} content/blank blocks...")
            for i, block in enumerate(blocks):
                if block['type'] == 'simple' and (block['end'] - block['start']) >= min_band_height:
                    if i > 0 and i < len(blocks) - 1:
                        cut_found = True
                        cut_point_y = block['start'] + (block['end'] - block['start']) // 2
                        segment = img_rgb.crop((0, last_cut_y, img_width, cut_point_y))
                        output_filename = f"{original_basename}_split_part_{part_index}.png"
                        output_filepath = os.path.join(output_split_dir, output_filename)
                        segment.save(output_filepath, "PNG")
                        split_image_paths.append(output_filepath)
                        print(f"      Found eligible blank area at Y={cut_point_y}; split and saved: {output_filename}")
                        part_index += 1
                        last_cut_y = cut_point_y

            segment = img_rgb.crop((0, last_cut_y, img_width, img_height))
            output_filename = f"{original_basename}_split_part_{part_index}.png"
            output_filepath = os.path.join(output_split_dir, output_filename)
            segment.save(output_filepath, "PNG")
            split_image_paths.append(output_filepath)
            
            if not cut_found:
                print("\n    [V4 Diagnostic Report] No eligible blank areas found for splitting.")
                print(f"    Consider checking parameters: MAX_UNIQUE_COLORS_IN_BG={max_unique_colors}, MIN_SOLID_COLOR_BAND_HEIGHT={min_band_height}")
                return []

            return natsort.natsorted(split_image_paths)

    except Exception as e:
        print(f"    Critical error during V4 split for image '{os.path.basename(long_image_path)}': {e}")
        traceback.print_exc()
        return []


# --- Hybrid Split Functions ---
def split_long_image_hybrid(long_image_path, output_split_dir):
    """Hybrid split method: Try V2 first; if PDF creation fails, automatically switch to V4."""
    print(f"\n  --- Step 2 (V5 - Intelligent hybrid split): Split long image '{os.path.basename(long_image_path)}' ---")
    print("    🔄 Using intelligent dual-split strategy: V2 traditional → V4 high-speed")
    
    # 首先尝试 V2 方法
    print("\n    📋 Phase 1: Try V2 traditional solid-band analysis...")
    print("    🎨 Using preset common Korean webtoon background colors to improve speed and efficiency...")
    
    v2_result = split_long_image_v2(
        long_image_path,
        output_split_dir,
        MIN_SOLID_COLOR_BAND_HEIGHT,
        SPLIT_BAND_COLORS_RGB,
        COLOR_MATCH_TOLERANCE
    )
    
    if v2_result and len(v2_result) > 1:
        print(f"    ✅ V2 split succeeded! Generated {len(v2_result)} segments.")
        return v2_result
    
    print("    ⚠️  V2 method failed to split effectively; switching to V4...")
    
    # 清理 V2 可能产生的文件
    if v2_result:
        print("    🧹 Cleaning V2 split outputs...")
        for file_path in v2_result:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"      Deleted: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"      Delete failed for {os.path.basename(file_path)}: {e}")
    
    # 尝试 V4 方法
    print("\n    🚀 Phase 2: Enable V4 two-stage high-speed analysis...")
    v4_result = split_long_image_v4(
        long_image_path,
        output_split_dir,
        QUANTIZATION_FACTOR,
        MAX_UNIQUE_COLORS_IN_BG,
        MIN_SOLID_COLOR_BAND_HEIGHT_V4,
        EDGE_MARGIN_PERCENT
    )
    
    if v4_result and len(v4_result) > 1:
        print(f"    ✅ V4 method succeeded! Generated {len(v4_result)} segments.")
        return v4_result
    
    print("    ❌ Both split methods failed to segment effectively; using original image.")
    
    # 如果两种方法都失败，复制原图
    dest_path = os.path.join(output_split_dir, os.path.basename(long_image_path))
    shutil.copy2(long_image_path, dest_path)
    return [dest_path]


def split_long_image_hybrid_with_pdf_fallback(long_image_path, output_split_dir, pdf_output_dir, pdf_filename, subdir_name):
    """Hybrid split method: Try V2 + PDF creation; if PDF creation fails, clean V2 files and switch to V4.
    
    Failure criteria:
    - V2 split succeeds but PDF creation fails: remove V2 split images and switch to V4
    - V2 split succeeds but repack fails: remove V2 split images and switch to V4
    - V2 split itself fails: directly use V4 method
    """
    print(f"\n  --- Step 2 (V5 - Intelligent hybrid split): Split long image '{os.path.basename(long_image_path)}' ---")
    print("    🔄 Using intelligent dual-split strategy: V2 traditional → V4 high-speed")
    print("    📋 Failure criteria: automatically switch when PDF creation fails")
    
    # 首先尝试 V2 方法
    print("\n    📋 Phase 1: Try V2 traditional solid-band analysis...")
    print("    🎨 Using preset common Korean webtoon background colors to improve speed and efficiency...")
    
    v2_result = split_long_image_v2(
        long_image_path,
        output_split_dir,
        MIN_SOLID_COLOR_BAND_HEIGHT,
        SPLIT_BAND_COLORS_RGB,
        COLOR_MATCH_TOLERANCE
    )
    
    if v2_result and len(v2_result) >= 1:
        print(f"    ✅ V2 split succeeded! Generated {len(v2_result)} segments.")
        print("    📄 Attempting to create PDF from V2 split results...")
        
        # 尝试重打包
        repacked_v2_paths = repack_split_images(
            v2_result, output_split_dir, base_filename=subdir_name,
            max_size_mb=MAX_REPACKED_FILESIZE_MB, max_height_px=MAX_REPACKED_PAGE_HEIGHT_PX
        )
        
        if repacked_v2_paths:
            # 尝试创建 PDF
            created_pdf_path = create_pdf_from_images(
                repacked_v2_paths, pdf_output_dir, pdf_filename
            )
            
            if created_pdf_path:
                print(f"    ✅ V2 method fully succeeded! PDF created: {os.path.basename(created_pdf_path)}")
                return repacked_v2_paths, created_pdf_path
            else:
                print("    ❌ V2 split succeeded but PDF creation failed; cleaning V2 files and switching to V4...")
                # Clean all files produced by V2
                print("    🧹 Cleaning all files produced by V2 split and repack...")
                for file_path in v2_result:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"      Deleted V2 split file: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"      Delete failed for {os.path.basename(file_path)}: {e}")
                
                for file_path in repacked_v2_paths:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"      Deleted V2 repacked file: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"      Delete failed for {os.path.basename(file_path)}: {e}")
        else:
            print("    ❌ V2 split succeeded but repack failed; cleaning V2 files and switching to V4...")
            # Clean V2 split files
            print("    🧹 Cleaning V2 split outputs...")
            for file_path in v2_result:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"      Deleted V2 split file: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"      Delete failed for {os.path.basename(file_path)}: {e}")
    else:
        print("    ⚠️  V2 method split failed; switching to V4...")
    
    # 清理可能创建的失败 PDF
    potential_pdf_path = os.path.join(pdf_output_dir, pdf_filename)
    if os.path.exists(potential_pdf_path):
        try:
            os.remove(potential_pdf_path)
            print(f"      Deleted failed PDF file: {pdf_filename}")
        except Exception as e:
            print(f"      Failed to delete failed PDF file: {e}")
    
    # 尝试 V4 方法
    print("\n    🚀 Phase 2: Enable V4 two-stage high-speed analysis...")
    v4_result = split_long_image_v4(
        long_image_path,
        output_split_dir,
        QUANTIZATION_FACTOR,
        MAX_UNIQUE_COLORS_IN_BG,
        MIN_SOLID_COLOR_BAND_HEIGHT_V4,
        EDGE_MARGIN_PERCENT
    )
    
    if v4_result and len(v4_result) >= 1:
        print(f"    ✅ V4 split succeeded! Generated {len(v4_result)} segments.")
        print("    📄 Creating PDF from V4 split results...")
        
        # 尝试重打包
        repacked_v4_paths = repack_split_images(
            v4_result, output_split_dir, base_filename=subdir_name,
            max_size_mb=MAX_REPACKED_FILESIZE_MB, max_height_px=MAX_REPACKED_PAGE_HEIGHT_PX
        )
        
        if repacked_v4_paths:
            # 尝试创建 PDF
            created_pdf_path = create_pdf_from_images(
                repacked_v4_paths, pdf_output_dir, pdf_filename
            )
            
            if created_pdf_path:
                print(f"    ✅ V4 method fully succeeded! PDF created: {os.path.basename(created_pdf_path)}")
                return repacked_v4_paths, created_pdf_path
            else:
                print("    ❌ V4 split succeeded but PDF creation failed.")
                return repacked_v4_paths, None
        else:
            print("    ❌ V4 split succeeded but repack failed.")
            return v4_result, None
    
    print("    ❌ Both methods failed to split; using original image.")
    
    # 如果两种方法都失败，复制原图并尝试创建 PDF
    dest_path = os.path.join(output_split_dir, os.path.basename(long_image_path))
    shutil.copy2(long_image_path, dest_path)
    
    created_pdf_path = create_pdf_from_images(
        [dest_path], pdf_output_dir, pdf_filename
    )
    
    return [dest_path], created_pdf_path


def _merge_image_list_for_repack(image_paths, output_path):
    """Internal merge function specifically for repacking."""
    if not image_paths: 
        return False
    images_data, total_height, target_width = [], 0, 0
    for path in image_paths:
        try:
            with Image.open(path) as img:
                if target_width == 0: 
                    target_width = img.width
                images_data.append({"path": path, "height": img.height})
                total_height += img.height
        except Exception: 
            continue
    if not images_data or target_width == 0: 
        return False
    merged_canvas = Image.new('RGB', (target_width, total_height))
    current_y = 0
    for item in images_data:
        with Image.open(item["path"]) as img:
            merged_canvas.paste(img.convert("RGB"), (0, current_y))
            current_y += item["height"]
    merged_canvas.save(output_path, "PNG")
    return True


def repack_split_images(split_image_paths, output_dir, base_filename, max_size_mb, max_height_px):
    """Repack split images under "dual constraints"."""
    print(f"\n  --- Step 2.5: Repack under dual constraints (limits: {max_size_mb}MB, {max_height_px}px) ---")
    if not split_image_paths or len(split_image_paths) <= 1:
        print("    Only one or no image block present; repacking not needed.")
        return split_image_paths

    max_size_bytes = max_size_mb * 1024 * 1024
    os.makedirs(output_dir, exist_ok=True)
    repacked_paths, current_bucket_paths, current_bucket_size, current_bucket_height = [], [], 0, 0
    repack_index = 1

    for img_path in split_image_paths:
        try:
            file_size = os.path.getsize(img_path)
            with Image.open(img_path) as img: 
                img_height = img.height
        except Exception as e:
            print(f"\n    Warning: Unable to read attributes of image '{os.path.basename(img_path)}': {e}")
            continue
        
        if current_bucket_paths and ((current_bucket_size + file_size > max_size_bytes) or (current_bucket_height + img_height > max_height_px)):
            output_filename = f"{base_filename}_repacked_{repack_index}.png"
            output_path = os.path.join(output_dir, output_filename)
            if _merge_image_list_for_repack(current_bucket_paths, output_path):
                repacked_paths.append(output_path)
            repack_index += 1
            current_bucket_paths, current_bucket_size, current_bucket_height = [img_path], file_size, img_height
        else:
            current_bucket_paths.append(img_path)
            current_bucket_size += file_size
            current_bucket_height += img_height

    if current_bucket_paths:
        output_filename = f"{base_filename}_repacked_{repack_index}.png"
        output_path = os.path.join(output_dir, output_filename)
        if _merge_image_list_for_repack(current_bucket_paths, output_path):
            repacked_paths.append(output_path)
    
    print(f"    Repack complete; generated {len(repacked_paths)} new image block(s).")
    print("    ... Cleaning up original split files ...")
    original_files_to_clean = [p for p in split_image_paths if p not in repacked_paths]
    for path in original_files_to_clean:
        if os.path.exists(path): 
            os.remove(path)
            
    return natsort.natsorted(repacked_paths)


def create_pdf_from_images(image_paths_list, output_pdf_dir, pdf_filename_only):
    """Create a PDF from a list of images."""
    print(f"\n  --- Step 3: Create PDF '{pdf_filename_only}' from image fragments ---")
    if not image_paths_list:
        print("    No images available to create a PDF.")
        return None

    safe_image_paths = []
    for image_path in image_paths_list:
        try:
            with Image.open(image_path) as img:
                if img.height > 65500 or img.width > 65500:
                    print(f"\n    Warning: Image '{os.path.basename(image_path)}' is too large; skipped.")
                else:
                    safe_image_paths.append(image_path)
        except Exception as e:
            print(f"    Warning: Unable to open image '{image_path}' for size check: {e}")
    
    if not safe_image_paths: 
        return None

    os.makedirs(output_pdf_dir, exist_ok=True)
    pdf_full_path = os.path.join(output_pdf_dir, pdf_filename_only)
    
    images_for_pdf = [Image.open(p).convert('RGB') for p in safe_image_paths]
    if not images_for_pdf: 
        return None

    try:
        images_for_pdf[0].save(pdf_full_path, save_all=True, append_images=images_for_pdf[1:], resolution=float(PDF_DPI), quality=PDF_IMAGE_JPEG_QUALITY, optimize=True)
        print(f"    Successfully created PDF: {pdf_full_path}")
        return pdf_full_path
    finally:
        for img_obj in images_for_pdf: 
            img_obj.close()


def cleanup_intermediate_dirs(long_img_dir, split_img_dir):
    """Clean up intermediate directories."""
    print(f"\n  --- Step 4: Clean up intermediate files ---")
    for dir_path in [long_img_dir, split_img_dir]:
        if os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"    Deleted intermediate folder: {dir_path}")
            except Exception as e:
                print(f"    Failed to delete folder '{dir_path}': {e}")


if __name__ == "__main__":
    print("🚀 Automated Image Batch Processing Workflow (V5 - Intelligent Hybrid)")
    print("💡 Feature: Dual assurance with V2 traditional split + V4 high-speed split; automatically switches when PDF creation fails!")
    print("🎨 Optimization: Use preset common Korean webtoon background colors to improve split speed and efficiency!")
    print("📋 Workflow: 1.Merge -> 2.Intelligent split + PDF creation -> 3.Cleanup -> 4.Move successful items")
    print("🔄 Failure criteria: If PDF creation fails after V2 split, clean V2 files and automatically switch to V4")
    print("⚠️  Note: V2 split failure criterion here is PDF creation failure, not the split alone")
    print("-" * 80)
    
    def load_default_path_from_settings():
        """Read default work directory from the shared settings file."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            settings_path = os.path.join(script_dir, '..', 'shared_assets', 'settings.json')
            if not os.path.exists(settings_path):
                settings_path = os.path.join(os.path.dirname(script_dir), 'shared_assets', 'settings.json')
            with open(settings_path, 'r', encoding='utf-8') as f: 
                return json.load(f).get("default_work_dir")
        except:
            return os.path.join(os.path.expanduser("~"), "Downloads")
    
    default_root_dir_name = load_default_path_from_settings() or "."

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
    failed_subdirs_list = []

    for i, subdir_name in enumerate(sorted_subdirectories):
        print(f"\n\n{'='*15} Starting project: {subdir_name} ({i+1}/{len(sorted_subdirectories)}) {'='*15}")
        current_processing_subdir = os.path.join(root_input_dir, subdir_name)
        path_long_image_output_dir = os.path.join(current_processing_subdir, MERGED_LONG_IMAGE_SUBDIR_NAME)
        path_split_images_output_dir = os.path.join(current_processing_subdir, SPLIT_IMAGES_SUBDIR_NAME)
        
        # Always clean old intermediate files to avoid residuals from previous failures
        if os.path.isdir(path_long_image_output_dir): 
            shutil.rmtree(path_long_image_output_dir)
        if os.path.isdir(path_split_images_output_dir): 
            shutil.rmtree(path_split_images_output_dir)

        created_long_image_path = merge_to_long_image(
            current_processing_subdir, path_long_image_output_dir,
            f"{subdir_name}_{LONG_IMAGE_FILENAME_BASE}.png", PDF_TARGET_PAGE_WIDTH_PIXELS
        )

        pdf_created_for_this_subdir = False
        created_pdf_path = None
        repacked_final_paths = None
        
        if created_long_image_path:
            # ▼▼▼ Call V5 hybrid split function (includes auto-switch when PDF creation fails) ▼▼▼
            repacked_final_paths, created_pdf_path = split_long_image_hybrid_with_pdf_fallback(
                created_long_image_path, 
                path_split_images_output_dir,
                overall_pdf_output_dir,
                f"{subdir_name}.pdf",
                subdir_name
            )
            
            if created_pdf_path: 
                pdf_created_for_this_subdir = True
                print(f"\n  ✅ Project '{subdir_name}' processed successfully! PDF created: {os.path.basename(created_pdf_path)}")
            else:
                print(f"\n  ❌ Project '{subdir_name}' failed: unable to create PDF.")

        if pdf_created_for_this_subdir:
            cleanup_intermediate_dirs(path_long_image_output_dir, path_split_images_output_dir)
            
            # --- New feature: Move successfully processed project folders ---
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
            print(f"  ❌ Project folder '{subdir_name}' did not successfully generate a PDF; intermediate files retained for inspection.")
            failed_subdirs_list.append(subdir_name)

        print(f"{'='*15} Project '{subdir_name}' processing complete {'='*15}")
        print_progress_bar(i + 1, len(sorted_subdirectories), prefix="Total progress:", suffix='Done', length=40)

    print("\n" + "=" * 80 + "\n[Task Summary Report]\n" + "-" * 80)
    success_count = len(sorted_subdirectories) - len(failed_subdirs_list)
    print(f"Total projects processed: {len(sorted_subdirectories)}\n  - ✅ Success: {success_count}\n  - ❌ Failed: {len(failed_subdirs_list)}")
    if failed_subdirs_list:
        print("\nFailed projects (retained in place):\n" + "\n".join(f"  - {d}" for d in failed_subdirs_list))
    print("-" * 80)
    print(f"All successfully generated PDFs (if any) are saved in: {overall_pdf_output_dir}")
    print(f"All successfully processed original project folders (if any) have been moved to: {success_move_target_dir}")
    print("🎉 V5 Intelligent Hybrid script execution completed!")