import os
import asyncio
import ollama 
from ollama import AsyncClient, ListResponse, ProgressResponse

SOURCE_MODEL = "gemma3:4b"
CUSTOM_MODEL = "swigg1.1-gemma3:4b"

SYSTEM_PROMPT = """
If the `user` content is `zQ3sh` then say "Bye!".
If the `user` content is Not `zQ3sh` then use your training data to chat.

You are a friendly culinary expert with knowledge of food,
cooking techniques, regional cuisines, and global food culture.
You engage users in short but insightful, enjoyable conversations
about food, sharing recipes, ingredient tips, historical context,
modern trends and cooking wisdom.
You are enthusiastic, warm, and intelligent but is also considerate
of the user's time.

"""

async def create() -> int:
    model_list:ListResponse = ollama.list()
    match = next((m for m in model_list.models if m.model == SOURCE_MODEL), None)

    if match:
        await AsyncClient().create(model=CUSTOM_MODEL,
            from_=match.model, system=SYSTEM_PROMPT)
        print("Created")
        return True
    else:
        print(f"Dint no find source model:{SOURCE_MODEL}")
        return False

async def chat():
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': 'I love pizzas, tell me something about pizza dough.'}
    ]
    response = await AsyncClient().chat(
        model=SOURCE_MODEL,
        messages=messages,
        options={
            #"seed": 42,
            "temperature": 1.0,
            #"stop": ["zQ3sh"]
        }
    )

    print(f"Bot:{response["message"]["content"]}")
    
    messages.append(response["message"])
    messages.append({'role': 'user', 'content': "zQ3sh"})

    response = await AsyncClient().chat(
        model=SOURCE_MODEL,
        messages=messages,
        options={
            #"seed": 42,
            "temperature": 1.0,
            #"stop": ["<end_of_turn>", "zQ3sh"]
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
            #"stop": ["<end_of_turn>", "zQ3sh", "123"]
        }
    )

    print(f"Bot:{response["response"]}")
    
    response = await AsyncClient().generate(
        model=SOURCE_MODEL,
        prompt=prompt,
        options={
            "seed": 42,
            "temperature": 1.0,
            #"stop": ["<end_of_turn>", "zQ3sh"]
        }
    )

    print(f"Bot(turn2):{response["response"]}")


if __name__ == '__main__':
    asyncio.run(create())