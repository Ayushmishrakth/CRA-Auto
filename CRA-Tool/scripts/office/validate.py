#!/usr/bin/env python3
"""
Validate a DOCX file structure and XML integrity.
Usage: python3 validate.py output.docx
"""

import sys
import zipfile
from pathlib import Path
from lxml import etree


def validate(docx_path):
    """Validate DOCX file structure and XML."""
    docx_path = Path(docx_path)

    if not docx_path.exists():
        print(f"Error: {docx_path} not found")
        return False

    errors = []

    # Check if it's a valid ZIP
    try:
        with zipfile.ZipFile(docx_path, 'r') as docx:
            file_list = docx.namelist()

            # Check for essential files
            essential = [
                '[Content_Types].xml',
                '_rels/.rels',
                'word/document.xml',
            ]

            for f in essential:
                if f not in file_list:
                    errors.append(f"Missing essential file: {f}")

            # Validate XML files
            xml_files = [f for f in file_list if f.endswith('.xml')]
            for xml_file in xml_files:
                try:
                    with docx.open(xml_file) as f:
                        etree.parse(f)
                except etree.XMLSyntaxError as e:
                    errors.append(f"XML syntax error in {xml_file}: {e}")

    except zipfile.BadZipFile:
        errors.append("File is not a valid ZIP (DOCX) file")
    except Exception as e:
        errors.append(f"Validation error: {e}")

    # Report results
    if errors:
        print("✗ VALIDATION FAILED\n")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✓ VALIDATION PASSED")
        print(f"  File: {docx_path}")
        print(f"  Size: {docx_path.stat().st_size} bytes")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate.py output.docx")
        sys.exit(1)

    success = validate(sys.argv[1])
    sys.exit(0 if success else 1)
