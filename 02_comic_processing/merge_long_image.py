import os
from PIL import Image
import natsort  # Used for natural filename sorting (e.g., img1, img2, img10)

# --- Global Settings ---
# Supported image file extensions
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif')

# Output settings (can remain hard-coded or be made interactive later)
OUTPUT_SUBFOLDER_NAME = "merged_output"         # Name of subfolder created inside selected input directory for outputs
MERGED_IMAGE_FILENAME = "stitched_long_image.png" # Filename of the merged image
# --- End of Global Settings ---

def merge_images_vertically(image_folder_path, output_image_path):
    """
    Vertically merge all images in the specified folder into a single long image in filename order.

    Args:
        image_folder_path (str): Folder path containing source images.
        output_image_path (str): Full save path for the merged long image.
    """
    # image_folder_path has already been validated as a directory path
    
    try:
        image_filenames = [
            f for f in os.listdir(image_folder_path)
            if os.path.isfile(os.path.join(image_folder_path, f)) and f.lower().endswith(IMAGE_EXTENSIONS)
        ]
    except Exception as e:  # Should not happen if image_folder_path is valid dir, but good for safety
        print(f"Unexpected error reading input folder '{image_folder_path}': {e}")
        return

    if not image_filenames:
        print(f"No supported image files found in folder '{os.path.abspath(image_folder_path)}'.")
        print(f"Supported formats include: {', '.join(IMAGE_EXTENSIONS)}")
        return

    sorted_image_filenames = natsort.natsorted(image_filenames)

    print(f"\nFound {len(sorted_image_filenames)} images in directory '{os.path.abspath(image_folder_path)}'. They will be merged in the following order:")
    for name in sorted_image_filenames:
        print(f"  - {name}")

    images_info = []
    print("\nAnalyzing image dimensions...")
    for filename in sorted_image_filenames:
        filepath = os.path.join(image_folder_path, filename)
        try:
            with Image.open(filepath) as img:
                images_info.append({
                    "path": filepath,
                    "width": img.width,
                    "height": img.height
                })
        except Exception as e:
            print(f"Warning: Unable to open or read dimensions for image '{filename}'; skipping: {e}")

    valid_images_info = [info for info in images_info if "width" in info]
    if not valid_images_info:
        print("No valid images available to merge.")
        return

    total_height = sum(info['height'] for info in valid_images_info)
    max_width = max(info['width'] for info in valid_images_info)

    print(f"\nComputed merged image size: width = {max_width}px, height = {total_height}px")

    merged_image = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))

    current_y_offset = 0
    print("\nMerging images...")
    for item_info in valid_images_info:
        try:
            with Image.open(item_info["path"]) as img:
                img_rgba = img.convert("RGBA")
                x_offset = (max_width - img_rgba.width) // 2
                merged_image.paste(img_rgba, (x_offset, current_y_offset))
                current_y_offset += img_rgba.height
                print(f"  Pasted: {os.path.basename(item_info['path'])}")
        except Exception as e:
            print(f"Warning: Error while pasting image '{os.path.basename(item_info['path'])}', skipped: {e}")

    output_dir_for_image = os.path.dirname(output_image_path)
    if not os.path.exists(output_dir_for_image):
        try:
            os.makedirs(output_dir_for_image)
            print(f"\nCreated output subdirectory: {os.path.abspath(output_dir_for_image)}")
        except Exception as e:
            print(f"Error: Failed to create output subdirectory '{output_dir_for_image}': {e}")
            return


    try:
        print(f"\nSaving merged image (using maximum lossless compression; this may take some time)...")
        merged_image.save(output_image_path, format='PNG', optimize=True, compress_level=9)
        print(f"Image successfully merged and saved as: {os.path.abspath(output_image_path)}")
        file_size_mb = os.path.getsize(output_image_path) / (1024 * 1024)
        print(f"Final file size: {file_size_mb:.2f} MB")
    except Exception as e:
        print(f"Error: Failed to save the merged image: {e}")

if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow library is not installed.")
        print("Please run: pip install Pillow")
        exit()
    try:
        import natsort
    except ImportError:
        print("Error: natsort library is not installed.")
        print("Please run: pip install natsort")
        exit()

    print("Welcome to the image merge script!")
    print("-" * 30)

    # --- Interactive input directory retrieval ---
    default_input_directory_name = "input_images_to_merge"  # Default folder name
    selected_input_dir = ""

    while True:
        prompt_message = (
            f"Please enter the folder path containing images to merge.\n"
            f"(e.g., 'my_comics' or '/path/to/your/images')\n"
            f"If you press Enter, the script will try to use the '{default_input_directory_name}' folder in the current directory: "
        )
        user_provided_path = input(prompt_message).strip()

        if not user_provided_path:  # User pressed Enter, use default
            current_path_to_check = default_input_directory_name
            print(f"Attempting to use default path: ./{current_path_to_check}")
        else:
            current_path_to_check = user_provided_path
        
        # Convert to absolute path for clear display and checks
        abs_path_to_check = os.path.abspath(current_path_to_check)

        if os.path.isdir(abs_path_to_check):
            selected_input_dir = abs_path_to_check
            print(f"Selected input directory: {selected_input_dir}")
            break 
        else:
            print(f"Error: Path '{abs_path_to_check}' is not a valid directory or does not exist.")
            # Ask user whether to create the default directory (if they attempted default and it doesn't exist)
            if (not user_provided_path or current_path_to_check == default_input_directory_name) and not os.path.exists(abs_path_to_check):
                create_choice = input(f"Directory '{abs_path_to_check}' does not exist. Create it now? (y/n): ").lower()
                if create_choice == 'y':
                    try:
                        os.makedirs(abs_path_to_check)
                        print(f"Directory '{abs_path_to_check}' created. Please place images into this directory and rerun the script or specify another directory.")
                        # Re-loop, user may want to specify another path.
                    except Exception as e:
                        print(f"Failed to create directory '{abs_path_to_check}': {e}")
            print("-" * 30)  # Separator for next prompt

    # --- Input directory selection complete ---

    # Early feedback: check if selected directory has images
    found_images_in_dir = False
    try:
        for item in os.listdir(selected_input_dir):
            if os.path.isfile(os.path.join(selected_input_dir, item)) and item.lower().endswith(IMAGE_EXTENSIONS):
                found_images_in_dir = True
                break
    except Exception as e:
        print(f"Error checking directory '{selected_input_dir}' contents: {e}")
        # Let merge_images_vertically handle it if listdir fails later.

    if not found_images_in_dir:
        print(f"Notice: Preliminary check found no supported image files in '{selected_input_dir}'.")
        print(f"The script will continue, but if there are no eligible images, no merged image will be generated.")
        # continue_anyway = input("是否仍要继续处理此目录? (y/n): ").lower()
        # if continue_anyway != 'y':
        #     print("脚本已中止。")
        #     exit()
    print("-" * 30)

    # Build output path
    output_subdirectory_full_path = os.path.join(selected_input_dir, OUTPUT_SUBFOLDER_NAME)
    full_output_image_path = os.path.join(output_subdirectory_full_path, MERGED_IMAGE_FILENAME)

    # Call merge function
    merge_images_vertically(selected_input_dir, full_output_image_path)

    print("-" * 30)
    print("Script processing complete.")