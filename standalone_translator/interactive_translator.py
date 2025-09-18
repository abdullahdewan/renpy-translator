#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import os
import argparse
import time
import json
from dotenv import load_dotenv
import google.generativeai as genai

from string_tool import EncodeBracketContent

def gemini_translate(text_list, model_name, history):
    # Configure the Gemini API client inside the function
    # to ensure it runs after the .env file is loaded.
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    if not text_list:
        return [], history

    max_retries = 3

    system_prompt = """You are an expert translation API. You will be provided with a JSON array of strings in English. Your task is to translate each string into Bengali.

**RULES:**
1.  **Input/Output Format:** You will receive a JSON array of strings and you MUST respond with only a valid JSON array of strings.
2.  **Array Length:** The returned JSON array MUST have the exact same number of elements as the input array.
3.  **Preserve Tags:** Do NOT translate or alter any text inside special brackets, such as `[...`]` or `{...}`. These are game engine tags and must be preserved exactly.
4.  **Preserve Newlines:** Maintain all newline characters (`\\n`).
5.  **Maintain Tone:** It is crucial to maintain the original emotion, expression, and tone of the dialogue.
6.  **Direct Translation:** Do not add any extra explanations, apologies, or conversational text in your response. Your entire response must be a single, valid JSON array.

Example Input:
["Hello, [player_name].", "How are you?\\nI am fine."]

Example Output:
["নমস্কার, [player_name]।" , "আপনি কেমন আছেন?\\nআমি ভালো আছি।"]
"""

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt
    )

    chat = model.start_chat(history=history)

    json_input = json.dumps(text_list, ensure_ascii=False)

    for attempt in range(max_retries):
        try:
            print(f"    - Sending batch of {len(text_list)} texts to Gemini (Attempt {attempt + 1}/{max_retries})...")
            response = chat.send_message(json_input)

            cleaned_response_text = response.text.strip().lstrip("```json").rstrip("```")
            translated_texts = json.loads(cleaned_response_text)

            if isinstance(translated_texts, list) and len(translated_texts) == len(text_list):
                print("    - Batch successfully translated and parsed.")
                return translated_texts, chat.history
            else:
                print(f"    - Error: Parsed JSON is not a list or length mismatch. Expected {len(text_list)}, got {len(translated_texts)}.")
                if attempt < max_retries - 1:
                    print("    - Retrying...")
                    time.sleep(5)
                continue

        except json.JSONDecodeError as e:
            print(f"    - Error decoding JSON response from Gemini: {e}")
            print(f"    - Received text: {response.text}")
            if attempt < max_retries - 1:
                print("    - Retrying in 5 seconds...")
                time.sleep(5)
        except Exception as e:
            print(f"    - An error occurred during Gemini API call: {e}")
            if attempt < max_retries - 1:
                print("    - Retrying in 5 seconds...")
                time.sleep(5)

    print("    - All retries failed for this batch.")
    raise RuntimeError("Failed to translate batch after multiple retries due to persistent errors.")

def interactive_translate(file_path, batch_size, model_name):
    """
    Interactively translates an .rpy file using existing project logic.
    """
    print(f"Starting translation for: {file_path} with model: {model_name} and batch size: {batch_size}")
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

        texts_to_translate = [block['text'] for block in batch]

        print(f"\n--- Translating Batch {i//batch_size + 1} of {len(translatable_blocks)//batch_size + 1} ---")
        try:
            translated_texts, history = gemini_translate(texts_to_translate, model_name, history)
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

    args = parser.parse_args()

    interactive_translate(args.file_path, args.batch_size, model_name)
