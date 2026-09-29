from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
documents = [
    """
    Employees are entitled to 20 days of annual leave
    per calendar year. Leave requests must be submitted
    through the HR portal.
    """,

    """
    Employees can claim medical reimbursement by
    submitting valid medical documents through the
    reimbursement portal.
    """,

    """
    Employees may work from home according to the
    company's hybrid work policy and manager approval.
    """,

    """
    The company holiday calendar is published at the
    beginning of each calendar year.
    """
]

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

document_embeddings = model.encode(
    documents
)


def retrieve(query, top_k=2):

    query_embedding = model.encode(
        [query]
    )

    scores = cosine_similarity(
        query_embedding,
        document_embeddings
    )[0]

    ranked_indices = scores.argsort()[::-1]

    results = []

    for index in ranked_indices[:top_k]:

        results.append({
            "document": documents[index],
            "score": float(scores[index])
        })

    return results

results = retrieve(
    "How many annual leaves do I get?"
)

for result in results:

    print("Score:", result["score"])
    print(result["document"])