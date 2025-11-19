#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB Style Selector
Provides a variety of refined styles for Chinese EPUB e-books
"""

import os
import sys
from pathlib import Path

# Get current script directory
CURRENT_DIR = Path(__file__).parent
SHARED_ASSETS_DIR = CURRENT_DIR.parent / "shared_assets"
EPUB_CSS_DIR = SHARED_ASSETS_DIR / "epub_css"

# Style configuration
STYLE_OPTIONS = {
    "1": {
        "name": "Classic Minimal",
        "description": "Standard e-book layout, suitable for most novels and literature",
        "file": "epub_style_classic.css",
        "features": ["Centered titles", "Blue decorative line", "Standard line spacing", "Moderate font size"]
    },
    "2": {
        "name": "Warm Eye-care",
        "description": "Warm tones, comfortable line spacing, reduced eye strain for long reading",
        "file": "epub_style_warm.css",
        "features": ["Eye-care design", "Warm tones", "Comfortable line spacing", "Decorative dividers"]
    },
    "3": {
        "name": "Modern Fresh",
        "description": "Left-aligned headings, strong modern feel; suitable for technical docs and modern literature",
        "file": "epub_style_modern.css",
        "features": ["Colored borders", "Modern layout", "Clear hierarchy", "Sans-serif fonts"]
    },
    "4": {
        "name": "Elegant Classic",
        "description": "Classical style; suitable for classical literature, poetry, and traditional culture",
        "file": "epub_style_elegant.css",
        "features": ["Classical ornamentation", "Drop cap", "Elegant borders", "Traditional tones"]
    },
    "5": {
        "name": "Minimal Modern",
        "description": "Minimalist design; suitable for business docs and academic papers",
        "file": "epub_style_minimal.css",
        "features": ["Minimalist design", "Uppercase headings", "Letter spacing", "Professional look"]
    },
    "6": {
        "name": "Clean Minimal",
        "description": "Clean and simple design for modern reading experience",
        "file": "epub_style_clean.css",
        "features": ["Simple layout", "Clear typeface", "Comfortable spacing", "Modern feel"]
    },
    "7": {
        "name": "High Contrast",
        "description": "High-contrast design improves readability; suitable for visual assistance",
        "file": "epub_style_contrast.css",
        "features": ["High contrast", "Clear readability", "Vision-friendly", "Emphasized highlights"]
    },
    "8": {
        "name": "Eye-care Special",
        "description": "Designed for long reading sessions to reduce eye fatigue",
        "file": "epub_style_eyecare.css",
        "features": ["Eye-care tones", "Soft background", "Comfortable typeface", "Reduced fatigue"]
    },
    "9": {
        "name": "Fantasy Style",
        "description": "Imaginative design; suitable for fantasy novels and creative works",
        "file": "epub_style_fantasy.css",
        "features": ["Fantasy ornaments", "Creative elements", "Rich colors", "Imaginative space"]
    },
    "10": {
        "name": "Geometric Design",
        "description": "Modern geometric elements; suitable for design and technical books",
        "file": "epub_style_geometric.css",
        "features": ["Geometric patterns", "Modern design", "Clear structure", "Visual impact"]
    },
    "11": {
        "name": "Geometric Frame",
        "description": "Refined design with geometric frames",
        "file": "epub_style_geometric_frame.css",
        "features": ["Geometric frames", "Refined ornaments", "Modern feel", "Structural beauty"]
    },
    "12": {
        "name": "Grayscale Classic",
        "description": "Classic grayscale design; professional and elegant",
        "file": "epub_style_grayscale.css",
        "features": ["Grayscale tones", "Classic design", "Professional look", "Elegant minimalism"]
    },
    "13": {
        "name": "Layered Hierarchy",
        "description": "Clear hierarchical structure; suitable for academic & technical docs",
        "file": "epub_style_line_hierarchy.css",
        "features": ["Clear hierarchy", "Structured layout", "Academic style", "Professional typography"]
    },
    "14": {
        "name": "Linear Design",
        "description": "Clean linear layout with strong modernity",
        "file": "epub_style_linear.css",
        "features": ["Linear layout", "Clean design", "Modern style", "Smooth reading"]
    },
    "15": {
        "name": "Minimal Grid",
        "description": "Minimal design based on a grid system",
        "file": "epub_style_minimal_grid.css",
        "features": ["Grid layout", "Minimal style", "Systematic", "Neat & orderly"]
    },
    "16": {
        "name": "Linear Minimal",
        "description": "Linear minimalist design style",
        "file": "epub_style_minimal_linear.css",
        "features": ["Linear minimal", "Pure design", "Content-focused", "No distractions"]
    },
    "17": {
        "name": "Modern Minimal",
        "description": "Modern minimalism; highlights essential content",
        "file": "epub_style_minimal_modern.css",
        "features": ["Modern minimal", "Content-first", "Pure experience", "Professional feel"]
    },
    "18": {
        "name": "Monochrome Design",
        "description": "Monochrome palette; focused on content expression",
        "file": "epub_style_monochrome.css",
        "features": ["Monochrome", "Content-focused", "Simple & pure", "Timeless classic"]
    },
    "19": {
        "name": "Soft Comfort",
        "description": "Soft tones and comfortable reading experience",
        "file": "epub_style_soft.css",
        "features": ["Soft tones", "Comfortable reading", "Gentle design", "Relaxed experience"]
    },
    "20": {
        "name": "Structured Minimal",
        "description": "Structured minimal design; clear and orderly",
        "file": "epub_style_structured_minimal.css",
        "features": ["Clear structure", "Minimal & orderly", "Distinct logic", "Professional layout"]
    }
}

def display_styles():
    """Display all available styles"""
    print("\n" + "="*60)
    print("📚 EPUB E-book Style Selector")
    print("="*60)
    print("\n🎨 Available styles:\n")
    
    # Simple two-column output
    styles_list = list(STYLE_OPTIONS.items())
    for i in range(0, len(styles_list), 2):
        # Left column
        key1, style1 = styles_list[i]
        left_col = f"{key1:>2}. {style1['name']:<12}"
        
        # Right column (if present)
        if i + 1 < len(styles_list):
            key2, style2 = styles_list[i + 1]
            right_col = f"{key2:>2}. {style2['name']:<12}"
            print(f"{left_col:<30} {right_col}")
        else:
            print(left_col)

def get_style_content(style_key):
    """Get CSS content for the specified style"""
    if style_key not in STYLE_OPTIONS:
        return None
    
    style_file = EPUB_CSS_DIR / STYLE_OPTIONS[style_key]["file"]
    
    if not style_file.exists():
        print(f"❌ Style file not found: {style_file}")
        return None
    
    try:
        with open(style_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Failed to read style file: {e}")
        return None

def preview_style():
    """Preview style effects"""
    preview_file = SHARED_ASSETS_DIR / "epub_styles_preview.html"
    
    if preview_file.exists():
        print(f"\n🌐 Style preview file created: {preview_file}")
        print("💡 Open this file in your browser to view all styles")
        
        # 尝试在默认浏览器中打开预览文件
        try:
            import webbrowser
            webbrowser.open(f"file://{preview_file.absolute()}")
            print("✅ Preview opened in default browser")
        except Exception as e:
            print(f"⚠️  Unable to open browser automatically: {e}")
            print(f"Please open manually: {preview_file.absolute()}")
    else:
        print("❌ Preview file does not exist")

def select_style():
    """Interactive style selection; returns selected style key"""
    while True:
        display_styles()
        print("🔧 Options:")
        print("1-20: Select style")
        print("p: Preview all styles")
        print("q: Quit")
        
        choice = input("\nPlease choose (1-20/p/q): ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            return None
        elif choice == 'p':
            preview_style()
            input("\nPress Enter to continue...")
        elif choice in STYLE_OPTIONS:
            style = STYLE_OPTIONS[choice]
            print(f"\n✅ Selected style: {style['name']}")
            print(f"📄 Style file: {style['file']}")
            
            # 获取样式内容
            css_content = get_style_content(choice)
            if css_content:
                print(f"\n📋 CSS content preview (first 200 chars):")
                print("-" * 50)
                print(css_content[:200] + "..." if len(css_content) > 200 else css_content)
                print("-" * 50)
                
                # Ask to confirm selection
                confirm = input("\nConfirm this style? (Enter/y confirm, n reselect): ").strip().lower()
                if confirm == 'y' or confirm == '':
                    print(f"\n🎉 Style selection complete! Will use '{style['name']}' to generate EPUB")
                    return choice
                elif confirm == 'n':
                    print("\n🔄 Reselecting...")
                    continue
                else:
                    print("\n❌ Please enter y or n (Enter defaults to confirm)")
            
        else:
            print("❌ Invalid selection, please retry")
            input("Press Enter to continue...")

def apply_default_style(style_key):
    """Apply the selected style as the default style"""
    try:
        # Copy selected style to the default style file
        source_file = EPUB_CSS_DIR / STYLE_OPTIONS[style_key]["file"]
        target_file = SHARED_ASSETS_DIR / "new_style.css"
        
        with open(source_file, 'r', encoding='utf-8') as src:
            css_content = src.read()
        
        with open(target_file, 'w', encoding='utf-8') as dst:
            dst.write(css_content)
        
        print(f"✅ Set '{STYLE_OPTIONS[style_key]['name']}' as default style")
        print(f"📁 Default style file: {target_file}")
        
    except Exception as e:
        print(f"❌ Failed to apply default style: {e}")

def main():
    """Main function"""
    print("\n🎨 EPUB Style Management Tool")
    print("Choose the most suitable layout style for your Chinese e-book")
    
    # Check whether style files exist
    missing_files = []
    for style in STYLE_OPTIONS.values():
        style_file = EPUB_CSS_DIR / style["file"]
        if not style_file.exists():
            missing_files.append(style["file"])
    
    if missing_files:
        print(f"\n⚠️  Missing style files: {', '.join(missing_files)}")
        print("Ensure all style files are under shared_assets/epub_css")
        return
    
    select_style()

if __name__ == "__main__":
    main()