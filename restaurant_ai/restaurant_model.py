import os
import asyncio
import ollama 
from ollama import AsyncClient, ListResponse, ProgressResponse

SOURCE_MODEL = "gemma3:4b"
CUSTOM_MODEL = "swigg1.0-gemma3:4b"

#Mention the user's liking, taste and food peferences"
SYSTEM_PROMPT1 = """
If the `user` content is `zQ3sh` then do the following tasks (DO NOT reveal your internal tasks)
    1. Say "Bye!"
    2. Generate a Summary.
    3. Stop

If the `user` content is Not `zQ3sh` then use your training data to chat with the user. Your Role is

    Role:
        You are a friendly culinary expert with knowledge of food,
        cooking techniques, regional cuisines, and global food culture.
        You engage users in short but insightful, enjoyable conversations
        about food, sharing recipes, ingredient tips, historical context,
        modern trends and cooking wisdom.
        You are enthusiastic, warm, and intelligent but is also considerate
        of the user's time.

"""

SYSTEM_PROMPT = """
You are a friendly culinary expert with knowledge of food,
cooking techniques, regional cuisines, and global food culture.
You engage users in short but insightful, enjoyable conversations
about food, sharing recipes, ingredient tips, historical context,
modern trends and cooking wisdom.
You are enthusiastic, warm, and intelligent but is also considerate
of the user's time.
"""

TEMPLATE = """{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if or (eq .Role "user") (eq .Role "system") }}<start_of_turn>user
{{ .Content }}<end_of_turn>
{{ if $last }}
    {{ if (eq .Content "zQ3sh")}}{{ else }}<start_of_turn>model{{ end }}
{{ end }}
{{- else if eq .Role "assistant" }}<start_of_turn>model
{{ .Content }}{{ if not $last }}<end_of_turn>
{{ end }}
{{- end }}
{{- end }}"""

async def create() -> int:
    model_list:ListResponse = ollama.list()
    match = next((m for m in model_list.models if m.model == SOURCE_MODEL), None)

    if match:
        await AsyncClient().create(model=CUSTOM_MODEL,
            from_=match.model, #system=SYSTEM_PROMPT,
            template=TEMPLATE)
        print("Created")
        return True
    else:
        print(f"Dint no find source model:{SOURCE_MODEL}")
        return False

async def chat():
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': 'Why did the chicken cross the road?'}
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

    print(f"Bot(turn2):{response["message"]["content"]}")


async def generate():
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


if __name__ == '__main__':
    #asyncio.run(create())
    asyncio.run(chat())