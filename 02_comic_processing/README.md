============================================================
Module 02: Comic Processing Workflow (02_comic_processing)
============================================================
[Overview]
This module provides an automated image-processing pipeline that batch converts
folders containing sequential images (e.g., comic chapters) into optimized,
reader-friendly PDF files.

[Core Scripts]

🌟 image_processes_pipeline_v5.py (Highly recommended — Intelligent Hybrid, dual assurance)
image_processes_pipeline_v2.py (Recommended quick pipeline — works in most cases)
image_processes_pipeline_v3.py (Intelligent pipeline)
image_processes_pipeline_v4.py (Experimental pipeline)
convert_img_to_pdf.py (Direct conversion tool)
merge_pdfs.py (PDF merging tool)
convert_long_pdf.py (PDF-to-images tool)

[Usage]
All functionality in this module is integrated into the interactive menu of
the project’s root `main.py`.

In a terminal, navigate to the ContentForge root directory and run `python main.py`.

From the main menu choose "2. Comic Processing & Generation" and follow the prompts.

---------------------- Features and Usage Details ---------------------

🌟 [V5 Intelligent Hybrid Pipeline] Dual-assurance splitting + auto switching (highly recommended)

This is the latest intelligent hybrid version. It combines the strengths of V2 and V4,
providing a dual-assurance splitting strategy that succeeds across complex scenarios.

[Intelligent Dual Strategy]
1. Try V2’s traditional solid-band analysis first (suitable for most standard webtoons)
2. If V2’s PDF creation fails, automatically switch to V4’s two-stage high-speed analysis (better for complex backgrounds)
3. No manual choice or rerun needed — a single execution yields the best result

[Key Advantages]
  - Time-saving: No need to manually launch V4 when V2 struggles
  - Precise failure criterion: Final judgment is based on whether PDF creation succeeds, ensuring output quality
  - Dual assurance: Combines two algorithms to significantly increase success rate
  - User-friendly: Clear progress and status updates that make the process easy to follow
  - Stand-alone: Can be called independently; does not depend on the entire project structure

[Use Cases]
Suitable for all webtoon processing tasks, especially:
  - Images with complex backgrounds where traditional methods struggle
  - Batch jobs requiring a high success rate
  - Scenarios with strong efficiency requirements

[Technical Highlights]
  - V2 traditional strengths: Accurate solid-band detection for standard white/black backgrounds
  - V4 high-speed strengths: Two-stage color homogeneity analysis that efficiently handles complex backgrounds
  - Intelligent hybrid: Automatically chooses the most suitable method; no manual intervention
  - Error recovery: Automatically cleans V2 outputs and retries with V4 when V2 fails

[V3 Intelligent Pipeline] Merge, split, repack, and generate PDF

This is the most central, highly recommended pipeline. It turns a messy image
folder into a polished, shareable PDF in one workflow.

[Automated Steps]
1. Merge long image -> 2. Intelligent split -> 3. Repack by size -> 4. Generate PDF

[Use Cases]
Ideal for most webtoons intended for online reading. It smartly removes borders
introduced during stitching and repacks split content into reasonably sized image blocks
for faster transmission and comfortable reading.

[Core Techniques]

  - Borderless merging: Unifies image widths at step one, fundamentally avoiding white/black border issues caused by size differences.
  - Color-variance splitting: Uses advanced “color variance” analysis. By computing the dispersion of pixel colors per row, it accurately distinguishes “content” from “blank”, even for noisy or textured backgrounds, and avoids erroneous cuts in sparse areas like speech bubbles.
  - High-quality output: Performs a single high-quality resize and stores into the PDF with a relatively high JPEG quality (95) for sharp results.
  - NumPy acceleration: The core of the split algorithm is powered by NumPy’s efficient vectorized computations to greatly improve processing speed.

[Quick Conversion] Convert an image folder directly to PDF

  - Script: convert_img_to_pdf.py
  - Function: A simple and direct conversion tool. It scans all subfolders under the root
    that contain images and converts each subfolder directly into a corresponding PDF.
  - Processing logic: No merging or splitting. The N images in a folder become N pages in the PDF.
  - Use cases:
      - When the images are already paginated (e.g., scanned books).
      - When you don’t want any stitching or cropping — just quickly produce a PDF.

[PDF to Images] Convert PDFs back to images (supports long-page splitting)

  - Script: convert_long_pdf.py
  - Function: Converts PDF files back into sequential images.
  - Processing logic:
      - Automatically scans the specified directory for all PDFs.
      - Converts every page of each PDF into an image.
      - Core feature: If a PDF page is a long strip (e.g., webtoon), the script automatically splits it into multiple height-appropriate parts, named in order (e.g., `..._part_01.png`, `..._part_02.png`).
      - All images converted from a PDF are saved in their own subfolder named after the PDF for easy organization.
  - Use cases:
      - Extracting source images from PDF files.
      - Especially useful for PDFs containing long webtoon pages, restoring them into shorter images for further processing.
      - A pre-processing step for other workflows — for example, extract images, edit them, then use this module’s tools to regenerate a new PDF.