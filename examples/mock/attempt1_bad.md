# RAG

## Hook

Today we study RAG, which uses an LLM together with embeddings and a vector database to give answers that are much better than the answers that a normal chatbot would give you when you ask it something, because the whole system was designed with accuracy in mind and with the goal of solving the hallucination problem.

## What Is It?

RAG is a technique where the model is retrained on your documents so that it learns all of your private information and can then answer any question about it without ever needing to look anything up again, which is why companies like it so much.

## Why It Matters

It is better.

## How It Works

The documents are chunked and the chunks are turned into embeddings that are stored in a vector database from which they are later retrieved by a similarity search when the prompt arrives from the user.

## Recap

RAG is good.
