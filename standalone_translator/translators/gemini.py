import os
import time
import json
import google.generativeai as genai
from .base_translator import BaseTranslator

class GeminiTranslator(BaseTranslator):
    """
    A translator provider that uses the Google Gemini API.
    """
    def translate(self, batch_data, model_name, history, character_config):
        # Configure the Gemini API client inside the function
        # to ensure it runs after the .env file is loaded.
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        if not batch_data:
            return [], history

        max_retries = 3

        # Convert the character config to a string to embed in the prompt
        character_config_str = json.dumps(character_config, indent=2, ensure_ascii=False)

        system_prompt = f"""You are an expert translator for Ren'Py video games, specializing in translating English dialogue into natural, colloquial Bengali.

**Primary Goal:** Your main goal is to maintain consistency in character voice, tone, and relationships throughout the translation.

---
**CHARACTER AND RELATIONSHIP CONTEXT:**
You will be provided with the following JSON object describing the game's characters and their relationships. Use this as your primary guide for determining the correct level of formality (e.g., 'tumi' vs. 'apni') for each character's dialogue.
```json
{character_config_str}
```

---
**INPUT/OUTPUT FORMAT:**
- **Input:** You will receive a JSON array of objects. Each object has a "speaker" and a "dialogue" key.
- **Output:** You MUST respond with a simple JSON array of translated strings. The array must have the exact same number of elements as the input array.

---
**TRANSLATION STYLE GUIDE:**
1.  **Use Colloquial Bengali:** Translate into modern, natural, and conversational Bengali. Avoid overly formal or bookish language. The dialogue should sound like how people actually speak.
2.  **Maintain Consistency:** Use the `CHARACTER AND RELATIONSHIP CONTEXT` and the conversation history to maintain a consistent voice and form of address for each character. Infer the listener from the conversation history if possible.
3.  **Prefer Transliteration for Specific Words:** For certain English words, direct transliteration is preferred.
    -   Example: `Hello` should be `হ্যালো`, not `নমস্কার`.
    -   Example: `God` should be `গড`, not `ঈশ্বর`.
4.  **Use Common "Banglish":** Where it sounds natural in conversation, use common English words.
    -   Example: For "try the tea", a better translation is `"চা টা ট্রাই করতে চাই"`, not `"চা চেষ্টা করতে চাই"`.
5.  **Preserve Game Tags:** Do NOT translate or alter any text inside special brackets like `[...`]` or `{{...}}`.
6.  **Preserve Newlines:** Maintain all newline characters (`\\n`).
7.  **Response Format:** Your entire response must be a single, valid JSON array of strings, with no other text or explanations.
"""

        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt
        )

        chat = model.start_chat(history=history)

        # Serialize the list of dicts into a JSON string
        json_input = json.dumps(batch_data, ensure_ascii=False)

        for attempt in range(max_retries):
            try:
                print(f"    - Sending batch of {len(batch_data)} texts to Gemini (Attempt {attempt + 1}/{max_retries})...")
                response = chat.send_message(json_input)

                cleaned_response_text = response.text.strip().lstrip("```json").rstrip("```")
                translated_texts = json.loads(cleaned_response_text)

                if isinstance(translated_texts, list) and len(translated_texts) == len(batch_data):
                    print("    - Batch successfully translated and parsed.")
                    return translated_texts, chat.history
                else:
                    print(f"    - Error: Parsed JSON is not a list or length mismatch. Expected {len(batch_data)}, got {len(translated_texts)}.")
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
