import os
import sys
import zipfile
import xml.etree.ElementTree as ET
import html
import argparse
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import logging
import glob

# --- Logging setup ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class EpubAnalyzer:
    """A tool to comprehensively analyze EPUB files and return structured data."""

    def __init__(self, epub_path):
        if not Path(epub_path).exists():
            raise FileNotFoundError(f"File does not exist: {epub_path}")
        self.epub_path = Path(epub_path)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="epub_analyzer_"))
        self.ns = {
            'cn': 'urn:oasis:names:tc:opendocument:xmlns:container',
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'ncx': 'http://www.daisy.org/z3986/2005/ncx/'
        }

    def analyze(self) -> dict:
        """
        Execute the full analysis workflow and return a dictionary containing all data.
        """
        analysis_data = {'epub_filename': self.epub_path.name}
        try:
            self._extract_epub()
            opf_path = self._find_opf_path()
            analysis_data['opf_path'] = opf_path.relative_to(self.temp_dir)
            
            self._parse_opf(opf_path, analysis_data)
            
            ncx_item = analysis_data['manifest'].get(analysis_data.get('spine_toc_id'))
            # **修复**: 使用 opf_path.parent 作为基准来构建 NCX 文件的完整路径
            if ncx_item and ncx_item['exists']:
                full_ncx_path = opf_path.parent / ncx_item['href']
                analysis_data['toc'] = self._parse_ncx(full_ncx_path)
            else:
                analysis_data['toc'] = []

            analysis_data['file_tree'] = self._get_file_tree()
            return analysis_data

        finally:
            shutil.rmtree(self.temp_dir)
            logger.info(f"Temporary directory {self.temp_dir} has been cleaned for '{self.epub_path.name}'.")

    def _extract_epub(self):
        """Extract the EPUB file into the temporary directory."""
        with zipfile.ZipFile(self.epub_path, 'r') as zf:
            zf.extractall(self.temp_dir)
        logger.info(f"EPUB '{self.epub_path.name}' extracted to: {self.temp_dir}")

    def _find_opf_path(self) -> Path:
        """Parse container.xml to find the path to the .opf file."""
        container_path = self.temp_dir / 'META-INF' / 'container.xml'
        if not container_path.exists():
            raise FileNotFoundError("META-INF/container.xml not found.")
        
        tree = ET.parse(container_path)
        rootfile = tree.find('.//cn:rootfile', self.ns)
        if rootfile is None or not rootfile.get('full-path'):
            raise ValueError("Unable to find rootfile in container.xml.")
        
        return self.temp_dir / rootfile.get('full-path')

    def _parse_opf(self, opf_path: Path, analysis_data: dict):
        """Parse the OPF file."""
        tree = ET.parse(opf_path)
        
        # Metadata
        metadata = {}
        for elem in tree.findall('.//dc:*', self.ns):
            tag = elem.tag.split('}')[-1]
            metadata[f"dc:{tag}"] = elem.text if elem.text else ""
        analysis_data['metadata'] = metadata

        # Manifest
        manifest = {}
        opf_dir = opf_path.parent
        for item in tree.findall('.//opf:item', self.ns):
            item_id = item.get('id')
            href = item.get('href', '')
            media_type = item.get('media-type', '')
            file_path = opf_dir / href
            manifest[item_id] = {
                'href': href,
                'media_type': media_type,
                'exists': file_path.exists()
            }
        analysis_data['manifest'] = manifest

        # Spine
        spine = []
        spine_node = tree.find('.//opf:spine', self.ns)
        analysis_data['spine_toc_id'] = spine_node.get('toc') if spine_node is not None else None
        for itemref in spine_node.findall('.//opf:itemref', self.ns):
            spine.append(itemref.get('idref'))
        analysis_data['spine'] = spine

    def _parse_ncx(self, ncx_path: Path) -> list:
        """Parse the NCX file to obtain the Table of Contents; returns a list of dicts."""
        def parse_navpoint(element):
            nav_label = element.find('ncx:navLabel/ncx:text', self.ns)
            content = element.find('ncx:content', self.ns)
            
            point_data = {
                'text': nav_label.text if nav_label is not None else "Untitled",
                'src': content.get('src', '#') if content is not None else '#',
                'children': []
            }

            sub_points = element.findall('ncx:navPoint', self.ns)
            for sub_point in sub_points:
                point_data['children'].append(parse_navpoint(sub_point))
            return point_data

        tree = ET.parse(ncx_path)
        nav_map = tree.find('.//ncx:navMap', self.ns)
        toc_data = []
        if nav_map is not None:
            for nav_point in nav_map.findall('ncx:navPoint', self.ns):
                toc_data.append(parse_navpoint(nav_point))
        return toc_data

    def _get_file_tree(self) -> list:
        """生成物理文件结构的列表。"""
        def build_tree(dir_path: Path):
            tree_list = []
            items = sorted(list(dir_path.iterdir()), key=lambda p: (p.is_file(), p.name.lower()))
            for item in items:
                if item.is_dir():
                    tree_list.append({'name': item.name, 'type': 'folder', 'children': build_tree(item)})
                else:
                    tree_list.append({'name': item.name, 'type': 'file'})
            return tree_list
        return build_tree(self.temp_dir)

def generate_markdown_report(all_analysis_data: list, output_path: Path):
    """Generate a unified Markdown report based on the analysis data list."""
    md = f"# EPUB Analysis Report\n\n"
    md += f"**Report generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += f"A total of **{len(all_analysis_data)}** EPUB files were analyzed.\n\n"

    for data in all_analysis_data:
        md += f"---\n\n"
        md += f"## 📖 Filename: `{data['epub_filename']}`\n\n"

        # Metadata
        md += "### 1. Metadata\n\n"
        md += "| Field | Value |\n"
        md += "| :--- | :--- |\n"
        for k, v in data.get('metadata', {}).items():
            md += f"| `{k}` | {v} |\n"
        md += "\n"

        # Manifest
        md += "### 2. Manifest\n\n"
        md += "| ID | Path (href) | Media Type | File Status |\n"
        md += "| :--- | :--- | :--- | :--- |\n"
        for item_id, info in data.get('manifest', {}).items():
            status = "✅ Present" if info['exists'] else "❌ **Missing**"
            md += f"| `{item_id}` | `{info['href']}` | `{info['media_type']}` | {status} |\n"
        md += "\n"

        # Spine
        md += "### 3. Spine\n\n"
        for i, idref in enumerate(data.get('spine', [])):
            href = data.get('manifest', {}).get(idref, {}).get('href', 'Unknown')
            md += f"{i+1}. `{idref}` -> `{href}`\n"
        md += "\n"

        # TOC
        md += "### 4. Table of Contents (NCX)\n\n"
        def format_toc(toc_list, level=0):
            toc_md = ""
            for item in toc_list:
                indent = "  " * level
                src_file, _, src_anchor = item['src'].partition('#')
                anchor_part = f" -> `#{src_anchor}`" if src_anchor else ""
                toc_md += f"{indent}- {item['text']} (`{src_file}`{anchor_part})\n"
                if item['children']:
                    toc_md += format_toc(item['children'], level + 1)
            return toc_md
        toc_content = format_toc(data.get('toc', []))
        md += toc_content if toc_content else "TOC not found or could not be parsed.\n"
        md += "\n"

        # File Tree
        md += "### 5. Physical File Structure\n\n"
        def format_tree(tree_list, level=0):
            tree_md = ""
            for item in tree_list:
                indent = "  " * level
                icon = "📁" if item['type'] == 'folder' else "📄"
                tree_md += f"{indent}- {icon} `{item['name']}`\n"
                if 'children' in item:
                    tree_md += format_tree(item['children'], level + 1)
            return tree_md
        md += "```\n"
        md += format_tree(data.get('file_tree', []))
        md += "```\n\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"\n✅ Analysis report generated: {output_path}")

def main():
    """Script entry point."""
    parser = argparse.ArgumentParser(description="Analyze all EPUB files in the specified directory and generate a unified Markdown report.")
    parser.add_argument("target_dir", nargs='?', default='', help="Folder path containing EPUB files (optional).")
    
    args = parser.parse_args()
    target_dir_str = args.target_dir

    if not target_dir_str:
        # Fix: Set a user-specified default path
        default_path = "/Users/doudouda/Downloads/2/"
        prompt = f"Please enter the folder path to analyze (Press Enter to use: {default_path}): "
        target_dir_str = input(prompt).strip()
        if not target_dir_str:
            target_dir_str = default_path

    target_path = Path(target_dir_str)
    if not target_path.is_dir():
        print(f"Error: Path '{target_path}' is not a valid folder.", file=sys.stderr)
        sys.exit(1)

    epub_files = glob.glob(os.path.join(target_dir_str, '*.epub'))
    if not epub_files:
        print(f"No .epub files found in '{target_dir_str}'.")
        sys.exit(0)
    
    print(f"[*] Found {len(epub_files)} EPUB file(s) in the directory. Starting analysis...")
    
    all_analysis_data = []
    for epub_file in epub_files:
        try:
            print(f"  -> Analyzing: {os.path.basename(epub_file)}")
            analyzer = EpubAnalyzer(epub_file)
            analysis_data = analyzer.analyze()
            all_analysis_data.append(analysis_data)
        except Exception as e:
            print(f"    ❌ Error analyzing file '{os.path.basename(epub_file)}': {e}")
            logger.error(f"Error analyzing file '{epub_file}'.", exc_info=True)
    
    if all_analysis_data:
        report_path = target_path / "_EPUB_Analysis_Report.md"
        generate_markdown_report(all_analysis_data, report_path)

if __name__ == '__main__':
    main()
