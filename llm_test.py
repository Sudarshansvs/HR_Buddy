import ollama
from prompt import prompts
# response = ollama.chat(
#     model="llama3.2:3b",
#     messages=[
#         {
#             "role": "user",
#             "content": "What is an HR department?"
#         }
#     ]
# )

# print(response["message"]["content"])

import ollama

# response = ollama.chat(
#     model="llama3.2:3b",
#     messages=[prompts["prompt_sys_2"]['sys'], prompts["prompt_user_2"]['user']]
# )

# print(response["message"]["content"])




import ollama

import ollama


def ask_llama(question):

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "system",
                "content": """
                You are HR Buddy.

                Answer HR-related questions clearly
                and professionally.

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

question = input("Ask HR Buddy: ")

answer = ask_llama(question)

print("\nHR Buddy:")
print(answer)