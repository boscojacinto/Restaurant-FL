import torch
from transformers import XLNetTokenizer, XLNetModel

tokenizer = XLNetTokenizer.from_pretrained('xlnet-base-cased')
model = XLNetModel.from_pretrained('xlnet-base-cased',
                                   output_hidden_states=True,
                                   output_attentions=True)

inputs = tokenizer("Hello, world!", return_tensors="pt")
outputs = model(**inputs)

last_hidden_state = outputs[0]  # Final layer output
all_hidden_states = outputs[1]  # Tuple of 13 hidden states
attentions = outputs[2]         # Tuple of 12 attention weight matrices

print(len(all_hidden_states))  # 13 (embedding + 12 layers)
print(len(attentions))         # 12 (one per layer)

print(f"attentions:\n{attentions}")