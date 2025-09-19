#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import argparse

def generate_config(directory):
    """
    Scans a directory for .rpy files, extracts unique character tags,
    and generates a character_config.json file.
    """
    print(f"Scanning directory: {directory} for .rpy files...")
    character_tags = set()

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.rpy'):
                file_path = os.path.join(root, file)
                print(f"  - Processing {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            # Regex to find dialogue lines with potential character tags
                            match = re.match(r'^\s*(.*?)(".*")$', line.lstrip())
                            if match:
                                prefix = match.group(1).strip()
                                # Add to set if it's a valid tag (not a keyword)
                                if prefix and not prefix.startswith(('if', 'elif', 'else', 'while', 'for', 'return', 'jump', 'call', 'label', 'scene', 'show', 'hide', 'with', 'pass', 'def', 'class')):
                                    character_tags.add(prefix)
                except Exception as e:
                    print(f"    - Could not read file {file_path}: {e}")

    if not character_tags:
        print("No character tags found.")
        return

    print(f"\nFound {len(character_tags)} unique character tags: {sorted(list(character_tags))}")

    # Generate the JSON structure
    config = {"characters": {}}
    for tag in sorted(list(character_tags)):
        config["characters"][tag] = {
            "name": "",
            "personality": "",
            "relationships": {}
        }

    # Write the JSON file
    output_path = os.path.join(os.path.dirname(__file__), 'character_config.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully generated '{output_path}'.")
        print("Please edit this file to add character names, personalities, and relationships.")
    except Exception as e:
        print(f"\nError writing to file {output_path}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate a character_config.json template from .rpy files.'
    )
    parser.add_argument(
        'directory',
        type=str,
        help='The path to the directory containing .rpy files.'
    )

    args = parser.parse_args()
    generate_config(args.directory)
