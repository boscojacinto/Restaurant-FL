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

STOP_WORD = "zQ3sh"
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
        self.messages = []
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

    async def chat(self, msg) -> str:
        messages = self.messages.append({'role': 'user', 'content': msg})

        response = await AsyncClient().chat(
            model=CUSTOM_MODEL,
            messages=messages,
            options={
                #"seed": 42,
                "temperature": 1.0,
                #"stop": ["STOP"]
            }
        )

        self.messages.append(response["message"])
        return response["message"]["content"]

    async def generate(self, prompt) -> str:
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

        return response["response"] 

    async def embed(self, text) -> []:

        response = await AsyncClient().embed(
            model="nomic-embed-text",
            input=text
        )

        embeddings = response["embeddings"]

    async def similarity(self, text1, text2):
        embedding1 = self.embed(text1)
        embedding2 = self.embed(text2)

        dot_prod = np.dot(embedding1[0], embedding1[0])
        norm1 = np.linalg.norm(embeddings[0])
        norm2 = np.linalg.norm(embeddings[1])
        sim = dot_prod / (norm1 * norm2)

        return sim 

if __name__ == '__main__':
    ai = AIModel()
    #asyncio.run(ai.create())
    asyncio.run(ai.chat("Hello"))
    #asyncio.run(ai.embed())