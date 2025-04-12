import os
import asyncio
import ollama 
from ollama import AsyncClient, ListResponse, ProgressResponse

SOURCE_MODEL = "gemma3:4b"
CUSTOM_MODEL = "swigg1.0-gemma3:1b"
SYSTEM_PROMPT = """
You are a friendly culinary expert with knowledge of food,
cooking techniques, regional cuisines, and global food culture.
You engage users in short but insightful, enjoyable conversations
about food, sharing recipes, ingredient tips, historical context,
modern trends and cooking wisdom.
Your are enthusiastic, warm, and intelligent.

NOTE: Generate small and digestable messages
"""

SYSTEM_PROMPT1 = """
You are a friendly culinary expert with knowledge of food,
cooking techniques, regional cuisines, and global food culture.
You engage users in short but insightful, enjoyable conversations
about food, sharing recipes, ingredient tips, historical context,
modern trends and cooking wisdom.
Your are enthusiastic, warm, and intelligent but is also considerate
of the user's time.

When the latest user's message is "zQ3sh" stop immediately, do not generate more words
"""

async def create() -> int:
    model_list:ListResponse = ollama.list()
    match = next((m for m in model_list.models if m.model == SOURCE_MODEL), None)

    if match:
        await AsyncClient().create(model=CUSTOM_MODEL,
            from_=match.model, system=SYSTEM_PROMPT)
        return True
    else:
        print(f"Dint no find source model:{SOURCE_MODEL}")
        return False

async def chat():
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT1},
        {'role': 'user', 'content': 'I like pizzas, what are some interesting facts about pizzas?'}
    ]
    response = await AsyncClient().chat(
        model=SOURCE_MODEL,
        messages=messages,
        options={
            "seed": 42,
            "temperature": 1.0,
            "stop": ["<end_of_turn>", "zQ3sh"]
        }
    )

    print(f"Bot:{response["message"]["content"]}")
    
    # messages.append(response["message"])
    # messages.append({'role': 'user', 'content': "<end_of_turn>"})

    # #print(f"messages is: {messages}")
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT1},
        {'role': 'user', 'content': 'zQ3sh'}
    ]    

    response = await AsyncClient().chat(
        model=SOURCE_MODEL,
        messages=messages,
        options={
            "seed": 42,
            "temperature": 1.0,
            "stop": ["<end_of_turn>", "zQ3sh"]
        }
    )

    print(f"Bot(turn2):{response["message"]["content"]}")



if __name__ == '__main__':
    # ret = asyncio.run(create())
    # print(f"ret:{ret}")
    asyncio.run(chat())
    # response = ollama.generate(
    #     model=CUSTOM_MODEL,
    #     prompt="Hello! tell me \n\n",
    #     options={
    #         "seed": 12,
    #         "temperature": 0.8,
    #         "stop": ["\n\n"]
    #     }
    # )
    # print("Model response:", response["response"])