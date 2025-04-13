import os
import asyncio
import ollama 
import numpy as np
from ollama import AsyncClient, ListResponse, ProgressResponse

SOURCE_MODEL = "gemma3:4b"
CUSTOM_MODEL = "swigg1.0-gemma3:4b"

SYSTEM_PROMPT = """
You are a friendly culinary expert with knowledge of food,
cooking techniques, regional cuisines, and global food culture.
You engage users in short but insightful, enjoyable conversations
about food, sharing recipes, ingredient tips, historical context,
modern trends and cooking wisdom.
You are enthusiastic, warm, and intelligent but is also considerate
of the user's time.
"""

SUMMARY_QUERY = f"List the `user` personality in 3 words as follows \n(Personality: \n\r1. x\n\r2. y\n\r3. z\n\r)"

TEMPLATE = """{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if or (eq .Role "user") (eq .Role "system") }}<start_of_turn>user
{{ .Content }}<end_of_turn>
{{ if $last }}
    {{ if (eq .Content "zQ3sh")}}<start_of_turn>user{{ "List the `user` personality in 3 words as follows (Personality: x,   y,   z). Do NOT generate any more questions." }}<end_of_turn><start_of_turn>model{{ else }}<start_of_turn>model{{ end }}
{{ end }}
{{- else if eq .Role "assistant" }}<start_of_turn>model
{{ .Content }}{{ if not $last }}<end_of_turn>
{{ end }}
{{- end }}
{{- end }}"""

class AIModel:
    def __init__(self):
        pass

    async def create(self) -> int:
        model_list:ListResponse = ollama.list()
        match = next((m for m in model_list.models if m.model == SOURCE_MODEL), None)

        if match:
            await AsyncClient().create(model=CUSTOM_MODEL,
                from_=match.model, system=SYSTEM_PROMPT,
                template=TEMPLATE)
            print("Created")
            return True
        else:
            print(f"Dint no find source model:{SOURCE_MODEL}")
            return False

    async def chat(self):
        messages = [
        {'role': 'user', 'content': 'I love chinese, but hate the MSG added in the dishes. Why is MSG added?'}
        ]

        response = await AsyncClient().chat(
            model=CUSTOM_MODEL,
            messages=messages,
            options={
                #"seed": 42,
                "temperature": 1.0,
                #"stop": ["STOP"]
            }
        )

        print(f"Bot:{response["message"]["content"]}")
        
        messages.append(response["message"])
        messages.append({'role': 'user', 'content': "zQ3sh"})

        response = await AsyncClient().chat(
            model=CUSTOM_MODEL,
            messages=messages,
            options={
                #"seed": 42,
                "temperature": 1.0,
                #"stop": ["STOP"]
            }
        )

        print(f"Bot(turn 2):{response["message"]["content"]}")

    async def generate(self):
        prompt = ""
        response = await AsyncClient().generate(
            model=SOURCE_MODEL,
            system=SYSTEM_PROMPT,
            prompt=prompt,
            options={
                "seed": 42,
                "temperature": 1.0,
                #"stop": ["STOP"]
            }
        )

        print(f"Bot:{response["response"]}")

        response = await AsyncClient().generate(
            model=SOURCE_MODEL,
            prompt=prompt,
            options={
                "seed": 42,
                "temperature": 1.0,
                #"stop": ["STOP"]
            }
        )

        print(f"Bot(turn2):{response["response"]}")

    async def embed(self):
        texts = [
        "Friendly, Enthusiastic, Insightful",
        "Enthusiastic, Friendly, Intelligent"
        ]

        response = await AsyncClient().embed(
            model="nomic-embed-text",
            input=texts
        )

        embeddings = response["embeddings"]

        for i, emb in enumerate(embeddings):
            print(f"Embedding for text {i+1}: {emb[:40]}")

        dot_prod = np.dot(embeddings[0], embeddings[1])
        norm1 = np.linalg.norm(embeddings[0])
        norm2 = np.linalg.norm(embeddings[1])
        sim = dot_prod / (norm1 * norm2)
        print(f"Similarity: {sim:.4f}")

if __name__ == '__main__':
    ai = AIModel()
    #asyncio.run(ai.create())
    asyncio.run(ai.chat())
    #asyncio.run(ai.embed())