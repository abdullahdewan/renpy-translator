#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import os
import argparse
import time
from dotenv import load_dotenv
import google.generativeai as genai

from string_tool import EncodeBracketContent

# Configure the Gemini API client
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def gemini_translate(text_list):
    """
    Translates a batch of texts using the Gemini API.
    """
    system_prompt = """You are an expert translator specializing in translating dialogue and user interface text for video games, specifically for the Ren'Py engine.
Your task is to translate the given text from English to Bengali accurately while preserving the original tone and style.

**CRITICAL INSTRUCTIONS:**
1.  **Preserve Tags:** Do NOT translate or alter any text inside special brackets, such as `[...`]` or `{...}`. These are game engine tags and must remain exactly as they are. For example, if you see `[player_name]`, you must return `[player_name]`.
2.  **Preserve Newlines:** Maintain all newline characters (`\\n`) exactly as they appear in the original text.
3.  **Translate Only the Text:** Only translate the narrative text, dialogue, and UI elements.

Provide only the translated text as a direct response, without any additional explanations or conversational text."""

    model = genai.GenerativeModel(
        model_name='gemini-pro',
        system_instruction=system_prompt
    )

    translated_list = []
    for text in text_list:
        if not text.strip():
            translated_list.append(text)
            continue

        try:
            print(f"    - Sending to Gemini: '{text[:40]}...'")
            response = model.generate_content(text)
            translated_text = response.text
            translated_list.append(translated_text)
            time.sleep(1) # Be respectful of API rate limits
        except Exception as e:
            print(f"    - Error translating '{text[:40]}...': {e}")
            print("    - Skipping this text and continuing.")
            translated_list.append(text) # Append original text on error

    return translated_list

def interactive_translate(file_path, batch_size):
    """
    Interactively translates an .rpy file using existing project logic.
    """
    print(f"Starting translation for: {file_path} with batch size: {batch_size}")
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
                    d = EncodeBracketContent(original_line, '"', '"')
                    if 'oriList' in d and len(d['oriList']) > 0:
                        original_text = d['oriList'][0][1:-1].replace('\\"', '"')
                        translatable_blocks.append({
                            'type': 'dialogue',
                            'line_index': original_line_index,
                            'text': original_text
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
    for i in range(0, len(translatable_blocks), batch_size):
        batch = translatable_blocks[i:i + batch_size]

        texts_to_translate = [block['text'] for block in batch]

        print(f"\n--- Translating Batch {i//batch_size + 1} of {len(translatable_blocks)//batch_size + 1} ---")
        translated_texts = gemini_translate(texts_to_translate)

        # Step 3: Update the content in memory
        for block, translated_text in zip(batch, translated_texts):
            line_index = block['line_index']
            original_line = lines[line_index] # Use original lines for indentation
            indentation = re.match(r'^\s*', original_line).group(0)
            escaped_translation = translated_text.replace('"', '\\"')

            if block['type'] == 'dialogue':
                new_lines[line_index] = f'{indentation}"{escaped_translation}" #done\n'
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

    parser = argparse.ArgumentParser(description='Translate .rpy files automatically.')
    parser.add_argument('file_path', type=str, help='The path to the .rpy file to translate.')
    parser.add_argument('--batch-size', type=int, default=10, help='The number of lines to translate in each batch.')

    args = parser.parse_args()

    interactive_translate(args.file_path, args.batch_size)
