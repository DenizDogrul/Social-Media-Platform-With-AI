import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("tag_Generator_api.env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_tags(content: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Return 3 tags. Each tag can be 1 to 3 words. Do NOT split phrases like 'deep learning'. Return ONLY a JSON array."
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            temperature=0.2
        )

        tags_text = response.choices[0].message.content
        print("GPT RESPONSE:", tags_text)

        tags = json.loads(tags_text)

        return tags

    except Exception as e:
        print("AI ERROR:", e)
        return ["general"]