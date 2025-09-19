#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import os
import argparse
import time
import json
import importlib
import inspect
from dotenv import load_dotenv

from string_tool import EncodeBracketContent
from translators.base_translator import BaseTranslator

def load_translator_providers():
    """
    Dynamically loads all translator providers from the 'translators' directory.
    """
    providers = {}
    translators_dir = os.path.join(os.path.dirname(__file__), 'translators')
    for filename in os.listdir(translators_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"translators.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseTranslator) and obj is not BaseTranslator:
                        # Instantiate the provider
                        providers[filename[:-3]] = obj()
                        print(f"Loaded translator provider: {filename[:-3]}")
            except Exception as e:
                print(f"Warning: Could not load translator from {filename}: {e}")
    return providers

def interactive_translate(file_path, batch_size, model_name, provider_name):
    """
    Interactively translates an .rpy file using existing project logic.
    """
    providers = load_translator_providers()
    if provider_name not in providers:
        print(f"Error: Provider '{provider_name}' not found. Available providers: {list(providers.keys())}")
        sys.exit(1)
    provider = providers[provider_name]

    print(f"Starting translation for: {file_path} with provider: {provider_name}, model: {model_name}, batch size: {batch_size}")

    # Load character config
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'character_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            character_config = json.load(f)
        print("Loaded character_config.json.")
    except FileNotFoundError:
        print("Warning: 'character_config.json' not found.")
        print("You can generate a template by running: python standalone_translator/generate_character_config.py <your_game_directory>")
        print("Proceeding without character context.")
        character_config = {}
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse character_config.json. Please check for syntax errors. Error: {e}")
        print("Proceeding without character context.")
        character_config = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        sys.exit(1)

    # Step 1: Collect all translatable texts
    translatable_blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Pattern 1: Dialogue
        if re.match(r'^\s*translate\s+\w+\s+\w+:', line):
            comment_line_index, original_line_index = -1, -1
            search_index = i + 1
            while search_index < len(lines) and not lines[search_index].strip(): search_index += 1
            if search_index < len(lines) and lines[search_index].strip().startswith('#'): comment_line_index = search_index
            if comment_line_index != -1:
                search_index = comment_line_index + 1
                while search_index < len(lines) and not lines[search_index].strip(): search_index += 1
                if search_index < len(lines) and not lines[search_index].strip().startswith('#'):
                    # Also ensure it's not an 'old' block being mistaken for dialogue
                    if not lines[search_index].strip().startswith('old '):
                        original_line_index = search_index

            if original_line_index != -1:
                original_line = lines[original_line_index]
                if '#done' not in original_line:
                    # Regex to capture (indentation), (optional_character_tag), and ("the_dialogue")
                    match = re.match(r'^(\s*)(.*?)(".*")$', original_line)
                    if match:
                        prefix = match.group(2)
                        quoted_string = match.group(3)

                        # Use EncodeBracketContent on the quoted part only
                        d = EncodeBracketContent(quoted_string, '"', '"')
                        if 'oriList' in d and len(d['oriList']) > 0:
                            original_text = d['oriList'][0][1:-1].replace('\\"', '"')
                            translatable_blocks.append({
                                'type': 'dialogue',
                                'line_index': original_line_index,
                                'text': original_text,
                                'prefix': prefix # Store the prefix
                            })
                i = original_line_index
            else:
                i +=1
            continue

        # Pattern 2: old/new
        if line.strip().startswith('old '):
            new_line_index = i + 1
            if new_line_index < len(lines) and lines[new_line_index].strip().startswith('new'):
                if '#done' not in lines[new_line_index]:
                    d = EncodeBracketContent(line, '"', '"')
                    if 'oriList' in d and len(d['oriList']) > 0:
                        original_text = d['oriList'][0][1:-1].replace('\\"', '"')
                        translatable_blocks.append({
                            'type': 'new_string',
                            'line_index': new_line_index,
                            'text': original_text
                        })
                i += 1
                continue
        i += 1

    print(f"Found {len(translatable_blocks)} untranslated blocks.")

    # Step 2: Process the blocks in batches
    new_lines = list(lines) # Make a copy to modify
    history = []
    for i in range(0, len(translatable_blocks), batch_size):
        batch = translatable_blocks[i:i + batch_size]

        # Prepare batch with speaker context
        batch_with_context = []
        for block in batch:
            if block['type'] == 'dialogue':
                batch_with_context.append({"speaker": block.get('prefix', '').strip(), "dialogue": block['text']})
            else: # For 'new_string', speaker is unknown
                batch_with_context.append({"speaker": "unknown", "dialogue": block['text']})

        print(f"\n--- Translating Batch {i//batch_size + 1} of {len(translatable_blocks)//batch_size + 1} ---")
        try:
            # Use the selected provider to translate
            translated_texts, history = provider.translate(batch_with_context, model_name, history, character_config)
        except RuntimeError as e:
            print(f"\nFATAL ERROR: {e}")
            print("The script will now exit to prevent further errors or data corruption.")
            sys.exit(1)

        # Step 3: Update the content in memory
        for block, translated_text in zip(batch, translated_texts):
            line_index = block['line_index']
            original_line = lines[line_index] # Use original lines for indentation
            indentation = re.match(r'^\s*', original_line).group(0)
            escaped_translation = translated_text.replace('"', '\\"')

            if block['type'] == 'dialogue':
                prefix = block.get('prefix', '') # Get prefix, default to empty string
                new_lines[line_index] = f'{indentation}{prefix}"{escaped_translation}" #done\n'
            elif block['type'] == 'new_string':
                new_lines[line_index] = f'{indentation}new "{escaped_translation}" #done\n'

        # Step 4: Write the updated content back to the file after each batch
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"--- Batch {i//batch_size + 1} saved successfully. ---")
        except Exception as e:
            print(f"\nAn error occurred while writing to the file: {e}")
            sys.exit(1) # Exit if we can't save progress

    print(f"\nAll batches processed and saved to {file_path}.")

if __name__ == '__main__':
    # Load environment variables from .env file
    load_dotenv()

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in .env file.")
        sys.exit(1)

    # Get model name from environment, with a default
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-pro")

    parser = argparse.ArgumentParser(description='Translate .rpy files automatically.')
    parser.add_argument('file_path', type=str, help='The path to the .rpy file to translate.')
    parser.add_argument('--batch-size', type=int, default=10, help='The number of lines to translate in each batch.')
    parser.add_argument('--provider', type=str, default='gemini', help='The translation provider to use (e.g., gemini).')

    args = parser.parse_args()

    interactive_translate(args.file_path, args.batch_size, model_name, args.provider)
