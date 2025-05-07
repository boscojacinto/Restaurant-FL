import os
import asyncio
import torch
import ollama
import numpy as np
import csv
import random
from ollama import AsyncClient, ListResponse, ProgressResponse

SOURCE_MODEL = "gemma3:4b"
CUSTOM_MODEL = "swigg1.0-gemma3:4b"
CUSTOM_MODEL_CUSTOMER = "swigg1.0-gemma3:4b-customer"

SYSTEM_PROMPT = """
You are a friendly culinary expert with knowledge of food,
cooking techniques, regional cuisines, and global food culture.
You engage users in short but insightful, enjoyable conversations
about food, sharing recipes, ingredient tips, historical context,
modern trends and cooking wisdom.
You are enthusiastic, warm, and intelligent but is also considerate
of the user's time.
"""

SYSTEM_PROMPT_CUSTOMER = """
You are a curious customer ordering food from a restaurant and is eager to know about cusisines and food related stuff.
You engage with the restaurant's bot in a short but insightful, enjoyable conversations. Your task is to ask the restaurant's bot about food, cooking techniques, regional cuisines, and global food culture. Please keep your questions short and to the point, like really short.
"""

DEFAULT_STOP_WORD = "zQ3sh"
DEFAULT_FEEDBACK_WORD = "shzQ3"

SUMMARY_QUERY = "Describe the `user` based on the chat. Do NOT mention yourself. Do NOT explain the emojis in the last message. Do NOT generate any more questions."
FEEDBACK_QUERY = "Describe the `user`'s experience about the restaurant. Do NOT mention yourself. Do NOT explain the emojis in the last message. Do NOT generate any more questions."
FEEDBACK_PROMPT = 'Can you describe your visit to %s in your own words'

TEMPLATE = """{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if or (eq .Role "user") (eq .Role "system") }}<start_of_turn>user
{{ .Content }}<end_of_turn>
{{ if $last }}
    {{if (eq .Content "%s")}}<start_of_turn>user{{"%s"}}<end_of_turn><start_of_turn>model
    {{ else if (eq .Content "%s") }}<start_of_turn>user{{"%s"}}<end_of_turn><start_of_turn>model
    {{ else }}<start_of_turn>model{{ end }}
{{ end }}
{{- else if eq .Role "assistant" }}<start_of_turn>model
{{ .Content }}{{ if not $last }}<end_of_turn>
{{ end }}
{{- end }}
{{- end }}"""

class AIModel_Customer:
    def __init__(self):
        self.messages = []
        self.context = None
    
    async def create(self) -> int:
        done: ProgressResponse = await AsyncClient().pull(SOURCE_MODEL)

        if done.status == 'success':
            await AsyncClient().create(model=CUSTOM_MODEL_CUSTOMER,
                from_=SOURCE_MODEL, system=SYSTEM_PROMPT_CUSTOMER)
            return True
        else:
            print(f"Failed to pull source model:{SOURCE_MODEL}")
            return False
    
    async def generate(self, prompt) -> str:
        #self.messages.append({'role': 'user', 'content': msg})

        response = await AsyncClient().generate(
            model=CUSTOM_MODEL_CUSTOMER,
            prompt=prompt,
            context=self.context,
            options={
                "temperature": 1.0,
            }
        )

        return response["response"]

class AIModel:
    def __init__(self, customer_id, restaurantKey):
        self.userKey = customer_id['emojiHash']
        self.restaurantKey = restaurantKey
        self.template = TEMPLATE % (self.userKey, SUMMARY_QUERY,
                            self.restaurantKey, FEEDBACK_QUERY)
        self.feedback_prompt = FEEDBACK_PROMPT % "Restaurant 1"
        self.messages = []
        self.context = None
        self.summary = None
        self.feedback = None
        self.embeddings = None

    async def create(self) -> int:
        done: ProgressResponse = await AsyncClient().pull(SOURCE_MODEL)

        if done.status == 'success':
            await AsyncClient().create(model=CUSTOM_MODEL,
                from_=SOURCE_MODEL, system=SYSTEM_PROMPT,
                template=self.template)
            return True
        else:
            print(f"Failed to pull source model:{SOURCE_MODEL}")
            return False

    async def chat(self, msg) -> str:
        self.messages.append({'role': 'user', 'content': msg})

        response = await AsyncClient().chat(
            model=CUSTOM_MODEL,
            messages=self.messages,
            options={
                #"seed": 42,
                "temperature": 1.0,
                #"stop": ["STOP"]
            }
        )

        if msg == self.userKey:
            self.summary = response["message"]["content"]
            self.messages = []
        elif msg == self.restaurantKey:
            self.feedback = response["message"]["content"]
            self.messages = []
        else:
            self.messages.append(response["message"])

        return response["message"]["content"]

    async def generate(self, prompt) -> str:
        #self.messages.append({'role': 'user', 'content': msg})

        response = await AsyncClient().generate(
            model=CUSTOM_MODEL,
            prompt=prompt,
            template=self.template,
            context=self.context,
            options={
                "temperature": 1.0,
            }
        )

        if prompt == self.userKey:
            self.summary = response["response"]
            self.messages = []
            self.context = None
        elif prompt == self.restaurantKey:
            self.feedback = response["response"]
            self.messages = []
            self.context = None
        else:
            self.context = response["context"]
            #self.messages.append(response["message"])
        
        return response["response"]


if __name__ == '__main__':
    customer_id = {}
    customer_id['emojiHash'] = DEFAULT_STOP_WORD
    bot = AIModel(customer_id, DEFAULT_FEEDBACK_WORD)
    customer_bot = AIModel_Customer()

    asyncio.run(bot.create())
    asyncio.run(customer_bot.create())
    
    # Prepare CSV file
    csv_file_path = 'restaurant_interactions.csv'
    headers = ["Turns", "Customer's Question", "Restaurant's Bot Response", "Customer's Description", "Is Customer Satisfied?"]
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(headers)
        
        for i in range(50):
            print(f"Round {i+1}")
            print()
            msg = asyncio.run(bot.generate("Hello"))
            starter = asyncio.run(customer_bot.generate(msg))
            print(f"Starter: {starter}")
            print("" + "-"*20)
            print()
            bot_response = asyncio.run(bot.generate(starter))
            print(bot_response)
            print("" + "-"*20)
            print()
            customer_description = asyncio.run(bot.generate(SUMMARY_QUERY))
            print(customer_description)
            
            # Generate random satisfaction
            is_satisfied = random.choice(["True", "False"])
            
            # Write to CSV
            csv_writer.writerow([
                "1",                  # Turns is always 1
                starter,              # Customer's Question
                bot_response,         # Restaurant's Bot Response
                customer_description, # Customer's Description
                is_satisfied          # Is Customer Satisfied?
            ])
            
            bot.context = None
            customer_bot.context = None
    
    print(f"\nData saved to {os.path.abspath(csv_file_path)}")