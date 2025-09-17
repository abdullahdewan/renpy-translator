#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import os

# Need to add src to path to import from string_tool
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
from string_tool import EncodeBracketContent

def interactive_translate(file_path):
    """
    Interactively translates an .rpy file using existing project logic.
    """
    print(f"Starting interactive translation for: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        sys.exit(1)

    new_lines = list(lines)
    i = 0
    while i < len(new_lines):
        line = new_lines[i]

        # Pattern 1: Dialogue
        if re.match(r'^\s*translate\s+\w+\s+\w+:', line):
            if i + 2 < len(new_lines):
                comment_line = new_lines[i+1]
                original_line = new_lines[i+2]
                if comment_line.strip().startswith('#') and not original_line.strip().startswith('#'):
                    d = EncodeBracketContent(original_line, '"', '"')
                    if 'oriList' in d and len(d['oriList']) > 0:
                        original_text = d['oriList'][0][1:-1].replace('\\"', '"')
                        print(f"\n--- Original (Line {i+3}) ---\n{original_text}")
                        translated_text = input("Enter translation: ")

                        indentation = re.match(r'^\s*', original_line).group(0)
                        escaped_translation = translated_text.replace('"', '\\"')
                        new_lines[i+2] = f'{indentation}"{escaped_translation}"\n'

                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(new_lines)
                        print("Updated.")
                    i += 2
                    continue

        # Pattern 2: old/new
        if line.strip().startswith('old '):
            new_line_index = i + 1
            if new_line_index < len(new_lines) and new_lines[new_line_index].strip().startswith('new'):
                d = EncodeBracketContent(line, '"', '"')
                if 'oriList' in d and len(d['oriList']) > 0:
                    original_text = d['oriList'][0][1:-1].replace('\\"', '"')
                    print(f"\n--- Original (Line {i+1}) ---\n{original_text}")
                    translated_text = input("Enter translation: ")

                    indentation = re.match(r'^\s*', new_lines[new_line_index]).group(0)
                    escaped_translation = translated_text.replace('"', '\\"')
                    new_lines[new_line_index] = f'{indentation}new "{escaped_translation}"\n'

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    print("Updated.")
                i += 1
                continue
        i += 1

    print("\nAll translations complete.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python src/interactive_translator.py <path_to_rpy_file>")
        sys.exit(1)

    rpy_file = sys.argv[1]
    interactive_translate(rpy_file)
