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
            # Found the start of a block, now search for the content lines
            comment_line_index = -1
            original_line_index = -1
            search_index = i + 1

            # Find the commented line, skipping blank lines
            while search_index < len(new_lines) and not new_lines[search_index].strip():
                search_index += 1
            if search_index < len(new_lines) and new_lines[search_index].strip().startswith('#'):
                comment_line_index = search_index

            # Find the original text line, skipping blank lines
            if comment_line_index != -1:
                search_index = comment_line_index + 1
                while search_index < len(new_lines) and not new_lines[search_index].strip():
                    search_index += 1
                if search_index < len(new_lines) and not new_lines[search_index].strip().startswith('#'):
                    original_line_index = search_index

            if original_line_index != -1:
                # We found the block
                original_line = new_lines[original_line_index]
                d = EncodeBracketContent(original_line, '"', '"')
                if 'oriList' in d and len(d['oriList']) > 0:
                    original_text = d['oriList'][0][1:-1].replace('\\"', '"')
                    print(f"\n--- Original (Line {original_line_index + 1}) ---\n{original_text}")
                    translated_text = input("Enter translation: ")

                    indentation = re.match(r'^\s*', original_line).group(0)
                    escaped_translation = translated_text.replace('"', '\\"')
                    new_lines[original_line_index] = f'{indentation}"{escaped_translation}"\n'

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    print("Updated.")

                i = original_line_index
            else:
                i +=1
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
