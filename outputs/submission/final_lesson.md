# Introduction to Retrieval‑Augmented Generation  

## Hook  
A student asks a chatbot for the date of the next exam, but the answer is old and wrong.  

## What Is It?  
Retrieval‑Augmented Generation, or RAG, is a method that helps a text‑creating computer program give up‑to‑date answers.  
The name has three parts: **retrieval** means finding information, **augmented** means adding that information, and **generation** means writing a response.  
A large language model, called an LLM, is a program that can write many kinds of text. RAG does not change the LLM’s internal rules. It only changes the text that the LLM receives as input.  

## Why It Matters  
An LLM only knows what was in its training data. That data stops at a certain date, so the model cannot answer questions about newer events.  
The LLM also does not see private documents unless they are given to it.  
When an LLM guesses facts, it may produce confident but false statements. This problem is called hallucination. RAG reduces hallucination by giving the model real source text to answer from.  
Updating a RAG system is cheap: you only replace the stored documents, not the whole model.  
RAG can also show which source passages were used, so users can verify the answer.  

## How It Works  

**Key words**  
- **Chunk** – a small piece of a document, such as a few paragraphs.  
- **Embedding** – a list of numbers that represents the meaning of a text piece. Texts with similar meaning have similar numbers.  
- **Vector database** – a storage system that holds embeddings and can quickly find those closest to a query.  
- **Prompt** – the text that is sent to an LLM as its input.  

**Steps**  
1. Load the documents you want the system to know.  
2. Split each document into chunks.  
3. Convert every chunk into an embedding.  
4. Store all embeddings in a vector database.  
5. When a user asks a question, turn the question into an embedding.  
6. Search the vector database for chunks whose embeddings are most similar to the question embedding.  
7. Combine the retrieved chunks and the user’s question into a prompt.  
8. Send the prompt to the LLM.  
9. The LLM writes an answer that uses the retrieved information.  

## Example  

### Simple analogy  
Think of a student who first looks up a textbook page before answering a teacher’s question. The textbook page is the retrieved chunk, and the student’s spoken answer is the generated response.  

### Example 1 – College scholarship query (Indian context)  
Imagine a college called **Sunrise College**. The college keeps a PDF that explains a new scholarship scheme.  

1. The PDF is loaded and split into chunks, each covering a rule or eligibility point.  
2. Each chunk becomes an embedding and is saved in a vector database.  
3. A student asks, “What are the eligibility requirements for the scholarship?”  
4. The system turns the question into an embedding and finds the chunk that lists the requirements.  
5. The retrieved chunk and the question are placed together in a prompt.  
6. The LLM replies, “The scholarship requires meeting the listed eligibility criteria.”  

### Example 2 – Local shop price list (Indian context)  
Imagine a shop named **Mithila Grocery** that keeps a digital price list for spices.  

1. The price list is broken into chunks, each containing a spice name and its price.  
2. Each chunk is turned into an embedding and stored.  
3. A customer asks, “What is the price of turmeric today?”  
4. The system finds the chunk that mentions the turmeric price.  
5. The chunk and the question form a prompt.  
6. The LLM answers, “The price of turmeric is shown in the retrieved information.”  

**Limitation** – If the retrieval step returns the wrong or incomplete chunk, the LLM will base its answer on that wrong information, and the answer will be incorrect.  

## Recap  
- RAG stands for Retrieval‑Augmented Generation.  
- It adds real documents to the input of a large language model.  
- The process uses chunks, embeddings, a vector database, and a prompt.  
- RAG helps keep answers up‑to‑date and reduces hallucination.  
- Updating knowledge only requires changing stored documents, not the model.  

## Check Yourself  
1. What does the word “embedding” mean in RAG?  
2. Why does RAG reduce the chance of hallucination?  
3. In the grocery example, what part of the system finds the price information?
