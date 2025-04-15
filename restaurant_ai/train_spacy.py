import spacy
from spacy.training import Example

# nlp = spacy.blank("en")
# ner = nlp.add_pipe("ner")
# ner.add_label("CUSTOM_PERSON")

# train_data = [
#     ("Grok is cool", {"entities": [(0, 4, "CUSTOM_PERSON")]})
# ]
# optimizer = nlp.begin_training()
# for _ in range(20):
#     for text, annotations in train_data:
#         doc = nlp.make_doc(text)
#         example = Example.from_dict(doc, annotations)
#         nlp.update([example], sgd=optimizer)

#nlp.to_disk("./ner_custom")

nlp = spacy.load("./ner_custom")

text = "Grok is working at xAI."
doc = nlp(text)

for ent in doc.ents:
    print(ent.text, ent.label_)