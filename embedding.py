# pip install sentence-transformers

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# embedding model
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

texts = [
    "What is the leave policy?",
    "How many vacation days can I take?",
    "What is the cafeteria menu?"
]

embeddings = model.encode(texts)

for text, embedding in zip(texts, embeddings):

    print(text)
    print("Vector size:", len(embedding))
    print(embedding[:5])
    print()

#Similarity search
query = model.encode(
    ["How many vacation days do I get?"]
)

scores = cosine_similarity(
    query,
    embeddings
)
print("Similarity scores:")
print(scores)



# Question
#    ↓
# Compare
#    ↓

# Leave policy       → high
# Vacation days      → high
# Cafeteria menu     → low