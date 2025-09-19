#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import argparse

def generate_config(directory):
    """
    Scans a directory for .rpy files, extracts character definitions (tag and name),
    and generates a character_config.json file.
    """
    print(f"Scanning directory: {directory} for character definitions in .rpy files...")
    character_data = {} # Use a dictionary to store tag: name

    # Regex to find lines like: define a = Character("Amelie", ...)
    char_def_regex = re.compile(r'^\s*define\s+([a-zA-Z0-9_]+)\s*=\s*Character\(\s*"(.*?)"')

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.rpy'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            match = char_def_regex.match(line)
                            if match:
                                char_tag = match.group(1)
                                char_name = match.group(2)
                                character_data[char_tag] = char_name
                                print(f"  - Found character: tag='{char_tag}', name='{char_name}'")
                except Exception as e:
                    print(f"    - Could not read file {file_path}: {e}")

    if not character_data:
        print("No character definitions found.")
        return

    print(f"\nFound {len(character_data)} unique characters: {sorted(character_data.keys())}")

    # Generate the JSON structure
    config = {"characters": {}}
    for tag, name in sorted(character_data.items()):
        config["characters"][tag] = {
            "name": name,
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
