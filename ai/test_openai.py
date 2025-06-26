import os
import httpx
from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    # api_key="ollama",
    # base_url="http://localhost:11434/v1"
)

response = client.chat.completions.create(
    #timeout=httpx.Timeout(60.0, read=2.0, write=1.0, connect=1.0),
    model="gpt-4.1-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "hello"}
    ]
)

print(response.choices[0].message.content)