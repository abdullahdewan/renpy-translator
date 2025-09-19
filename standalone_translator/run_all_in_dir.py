#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import argparse

def run_all_in_dir(directory, batch_size, provider_name):
    """
    Finds all .rpy files in a directory and runs the translator on them.
    """
    print(f"Searching for .rpy files in: {directory}")
    rpy_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.rpy'):
                rpy_files.append(os.path.join(root, file))

    if not rpy_files:
        print("No .rpy files found in the specified directory.")
        return

    print(f"Found {len(rpy_files)} .rpy files to process.")

    script_dir = os.path.dirname(__file__)
    translator_script_path = os.path.join(script_dir, 'interactive_translator.py')

    for rpy_file in rpy_files:
        print(f"\n--- Running translator for: {rpy_file} ---")
        command = [
            'python',
            translator_script_path,
            rpy_file,
            '--batch-size',
            str(batch_size),
            '--provider',
            provider_name
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running translator for {rpy_file}: {e}")
        except FileNotFoundError:
            print(f"Error: Could not find the Python interpreter. Make sure 'python' is in your system's PATH.")
            break

    print("\n--- All files processed. ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the translator on all .rpy files in a directory.')
    parser.add_argument('directory', type=str, help='The path to the directory to search for .rpy files.')
    parser.add_argument('--batch-size', type=int, default=10, help='The number of lines to translate in each batch.')
    parser.add_argument('--provider', type=str, default='gemini', help='The translation provider to use (e.g., gemini).')

    args = parser.parse_args()

    run_all_in_dir(args.directory, args.batch_size, args.provider)
