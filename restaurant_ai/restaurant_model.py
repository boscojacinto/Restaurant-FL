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

STOP_WORD = "zQ3sh"
SUMMARY_QUERY = "List the `user` personality in 3 words as follows: x,   y,   z. Do NOT prefix it with anyother word. Do NOT generate any more questions."

TEMPLATE = """{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if or (eq .Role "user") (eq .Role "system") }}<start_of_turn>user
{{ .Content }}<end_of_turn>
{{ if $last }}
    {{ if (eq .Content "zQ3sh")}}<start_of_turn>user{{ "Describe the `user` based on the chat. Do NOT mention yourself. Do NOT generate any more questions." }}<end_of_turn><start_of_turn>model{{ else }}<start_of_turn>model{{ end }}
{{ end }}
{{- else if eq .Role "assistant" }}<start_of_turn>model
{{ .Content }}{{ if not $last }}<end_of_turn>
{{ end }}
{{- end }}
{{- end }}"""

class AIModel:
    def __init__(self):
        self.messages = []
        self.summary = None
        self.embeddings = None

    async def create(self) -> int:
        model_list:ListResponse = ollama.list()
        match = next((m for m in model_list.models if m.model == SOURCE_MODEL), None)

        if match:
            await AsyncClient().create(model=CUSTOM_MODEL,
                from_=match.model, system=SYSTEM_PROMPT,
                template=TEMPLATE)
            return True
        else:
            print(f"Dint no find source model:{SOURCE_MODEL}")
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

        if msg == STOP_WORD:
            self.summary = response["message"]["content"]
        else:
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
    bot = AIModel()
    #asyncio.run(bot.create())
    # print(asyncio.run(bot.chat("I love Steak, but do NOT like Chinese or Butter Chicken")))
    # print(asyncio.run(bot.chat("zQ3sh")))
    
    # emb1 = asyncio.run(bot.xlnet_embed("The user is someone who enjoys Chinese food but is mindful of ingredients, specifically MSG. They’re curious about the reasons behind the ingredient’s use in Chinese cuisine and appreciates a knowledgeable, friendly culinary expert to guide them. They seem to be seeking information and practical advice about food choices and cooking techniques."))
    # emb2 = asyncio.run(bot.xlnet_embed("The user is someone who does NOT enjoy Chinese food and it NOT mindful of ingredients, specifically MSG. They’re NOT curious about the reasons behind the ingredient’s use in Chinese cuisine and doesnt appreciate a knowledgeable, friendly culinary expert to guide them. They dont seem to be seeking information and practical advice about food choices and cooking techniques."))
    # aentssyncio.run(bot.xlnet_similarity(emb1, emb2))

    emb1 = asyncio.run(bot.embed("The user demonstrates a clear interest in culinary history, particularly regarding popular dishes like Butter Chicken. They appreciate concise, informative explanations and are open to learning more about the origins and evolution of food. Their responses are brief, indicating a preference for direct information and a desire for focused conversation"))
    #emb2 = asyncio.run(bot.embed("The user enjoys discussing food enthusiastically, specifically Butter Chicken. They appreciate concise, informative responses and seem to value culinary knowledge and historical context. They engage in a light, conversational manner, indicating an interest in learning about food and its origins."))
    # asyncio.run(bot.similarity("That user enjoys steak, specifically, and has a clear preference against Chinese and Butter Chicken cuisine.", 
    #     "Based on our conversation, this user is someone who enjoys Chinese cuisine, is curious about the ingredients used in it, and is particularly sensitive to the use of MSG. They are interested in understanding the reasons behind culinary practices and are open to exploring alternative methods for achieving desired flavors. They appreciate informative and engaging explanations, and seem to value a thoughtful approach to food."))

    #asyncio.run(bot.similarity("The user is someone who enjoys Chinese food but is mindful of ingredients, specifically MSG. They’re curious about the reasons behind the ingredient’s use in Chinese cuisine and appreciates a knowledgeable, friendly culinary expert to guide them. They seem to be seeking information and practical advice about food choices and cooking techniques.", "The user is someone who does not enjoy Chinese food and it not mindful of ingredients, specifically MSG. They’re not curious about the reasons behind the ingredient’s use in Chinese cuisine and doesnt appreciate a knowledgeable, friendly culinary expert to guide them. They dont seem to be seeking information and practical advice about food choices and cooking techniques."))
    #asyncio.run(bot.similarity("Direct, Concise, Efficient", "Friendly, Enthusiastic, Considerate"))

    # bot.ner("The user demonstrates an interest in culinary history and specific dishes, particularly Butter Chicken. They appreciate concise information and are open to receiving recipes and ingredient tips. Their responses are brief, indicating a desire for focused conversation.")
    #asyncio.run(bot.embed())