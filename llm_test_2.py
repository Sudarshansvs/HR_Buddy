import ollama

from fastapi import FastAPI
from pydantic import BaseModel
from retriever import retrieve

app = FastAPI(
    title="HR Buddy API"
)


class HRQuestion(BaseModel):
    question: str


def ask_llama(question, context=""):

    system_prompt = """
    You are HR Buddy.

    Answer HR questions clearly and professionally.

    Do not invent company policies.
    If you do not have enough information,
    clearly say so.
    """

    if context:
        user_prompt = (
            f"Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{question}"
        )
    else:
        user_prompt = question

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )

    return response["message"]["content"]


@app.post("/ask")
def ask_hr(request: HRQuestion):

    results = retrieve(request.question)

    context = "\n\n".join(
        result["document"]
        for result in results
    )

    answer = ask_llama(request.question, context)

    return {
        "question": request.question,
        "answer": answer,
        "sources": results
    }