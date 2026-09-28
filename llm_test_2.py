import ollama

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(
    title="HR Buddy API"
)


class HRQuestion(BaseModel):
    question: str


def ask_llama(question):

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "system",
                "content": """
                You are HR Buddy.

                Answer HR questions clearly and professionally.

                Do not invent company policies.
                If you do not have enough information,
                clearly say so.
                """
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    return response["message"]["content"]


@app.post("/ask")
def ask_hr(request: HRQuestion):

    answer = ask_llama(request.question)

    return {
        "question": request.question,
        "answer": answer
    }