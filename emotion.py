from transformers import pipeline
classifier = pipeline("sentiment-analysis", model="michellejieli/emotion_text_classifier")
output = classifier("AI: Italians love their cheese! User: Indians love briyani")
print(output)