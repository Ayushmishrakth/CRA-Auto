#!/usr/bin/env python3
"""
Unpack a DOCX file to its constituent XML files.
Usage: python3 unpack.py template.docx output_dir/
"""

import sys
import zipfile
from pathlib import Path


def unpack(docx_path, output_dir):
    """Extract DOCX (ZIP) to directory structure."""
    docx_path = Path(docx_path)
    output_dir = Path(output_dir)

    if not docx_path.exists():
        print(f"Error: {docx_path} not found")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(docx_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print(f"Unpacked {docx_path} to {output_dir}")
    except Exception as e:
        print(f"Error unpacking: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 unpack.py template.docx output_dir/")
        sys.exit(1)

    unpack(sys.argv[1], sys.argv[2])
