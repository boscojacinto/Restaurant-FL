import os
import asyncio
import torch
import ollama
import spacy
import numpy as np
from transformers import XLNetTokenizer, XLNetModel
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

    async def embed(self, text):
        response = await AsyncClient().embed(
            model="nomic-embed-text",
            input=text
        )

        self.embeddings = response["embeddings"]
        return self.embeddings

    async def similarity(self, text1, text2):
        embedding1 = await self.embed(text1)
        embedding2 = await self.embed(text2)

        dot_prod = np.dot(embedding1[0], embedding2[0])
        norm1 = np.linalg.norm(embedding1[0])
        norm2 = np.linalg.norm(embedding2[0])
        print(f"norm1:{norm1}")
        print(f"norm2:{norm2}")
        print(f"(norm1 * norm2):{(norm1 * norm2)}")
        print(f"dot_prod:{dot_prod}")
        sim = dot_prod / (norm1 * norm2)
        print(f"sim:{sim}")
        return sim

    async def xlnet_similarity(self, embd1, embd2):

        dot_prod = torch.dot(embd1, embd2)
        norm1 = torch.linalg.norm(embd1)
        norm2 = torch.linalg.norm(embd2)
        sim = dot_prod / (norm1 * norm2)
        return sim

    async def xlnet_embed(self, text):
        tokenizer = XLNetTokenizer.from_pretrained('xlnet-base-cased')
        model = XLNetModel.from_pretrained('xlnet-base-cased',
                                    output_hidden_states=True,
                                    output_attentions=True).to("cpu")
        input_ids = torch.tensor([tokenizer.encode(text)]).to("cpu")
        all_hidden_states, all_attentions = model(input_ids)[-2:]
        rep = (all_hidden_states[-2][0] * all_attentions[-2][0].mean(dim=0).mean(dim=0).view(-1, 1)).sum(dim=0)
        return rep

    def ner(self, text):
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        keywords = [(ent.text, ent.label_) for ent in doc.ents]
        print(f"entities:{keywords}")

        keywords = [token.text for token in doc if token.pos_ in ["ADJ"]]
        print(f"adj:{keywords}")

        keywords = [token.text for token in doc if token.dep_ in ["nsubj", "dobj"]]
        print(f"sub, obj:{keywords}")


if __name__ == '__main__':
    customer_id = {}
    customer_id['emojiHash'] = DEFAULT_STOP_WORD
    bot = AIModel(customer_id, DEFAULT_FEEDBACK_WORD)
    asyncio.run(bot.create())