#!/usr/bin/env python3
"""
Pack a directory back into a DOCX file.
Usage: python3 pack.py unpacked_dir/ output.docx --original template.docx
"""

import sys
import zipfile
from pathlib import Path


def pack(input_dir, output_path, original_path=None):
    """Repack directory into DOCX (ZIP) file."""
    input_dir = Path(input_dir)
    output_path = Path(output_path)

    if not input_dir.exists():
        print(f"Error: {input_dir} not found")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as docx:
            # Walk through the unpacked directory
            for file_path in input_dir.rglob('*'):
                if file_path.is_file():
                    # Calculate relative path from input_dir
                    arcname = file_path.relative_to(input_dir)
                    docx.write(file_path, arcname)

        print(f"Packed {input_dir} to {output_path}")
    except Exception as e:
        print(f"Error packing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 pack.py unpacked_dir/ output.docx [--original template.docx]")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_path = sys.argv[2]
    original_path = None

    if len(sys.argv) > 3 and sys.argv[3] == "--original":
        if len(sys.argv) > 4:
            original_path = sys.argv[4]

    pack(input_dir, output_path, original_path)
