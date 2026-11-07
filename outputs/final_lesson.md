# Introduction to RAG (Retrieval-Augmented Generation)

## Hook

Imagine you ask a chatbot a question about your college fees. A chatbot is a computer program you can talk to. The chatbot gives you a date. But the date is wrong. The chatbot never saw your college notice. It just made a guess that sounded sure.

Wrong answers like this are a big problem. Retrieval-Augmented Generation is one way to fix it. By the end of this lesson, you will know what Retrieval-Augmented Generation is. You will know why people use it. You will also see how it works, step by step.

## What Is It?

Retrieval-Augmented Generation is often called RAG. The name looks hard, but the idea is simple. Let us break it into three parts.

Retrieval means finding relevant information from an external knowledge source. Augmented means adding that information to the input. Generation means letting a large language model (LLM) write the answer using that information. An LLM is a computer program that reads and writes human language.

So RAG is a way to let an AI look up facts before it answers. Think of an open-book exam. In a normal exam, you answer from memory. In an open-book exam, you can open the book and check. RAG gives the AI an open book.

An LLM only knows what was in its training data. Its training data stops at a cutoff date. It does not know newer events. An LLM also has not seen a person or company private documents unless they are given to it.

## Why It Matters

An LLM has common problems. RAG helps solve them.

One problem is old knowledge. An LLM stops learning at its cutoff date. Another problem is missing private data. A third problem is hallucination. Hallucination means an LLM produces text that sounds confident but is false or made up. 

RAG reduces hallucination by giving the model real source text to answer from. To update a RAG system's knowledge, you update the documents in the knowledge base. You do not need to retrain the model. This is usually cheaper and faster than retraining or fine-tuning. Fine-tuning means training an already trained model on new data. In RAG, the model's weights are not changed. RAG also can show which source passages were used, so users can verify the answer.

## How It Works

Here are the key words you need to know:
- A chunk is a small piece of a document, for example a few paragraphs.
- An embedding is a list of numbers that represents the meaning of a piece of text.
- A vector database is a special store that holds embeddings and can quickly find the ones most similar to a query embedding.
- A prompt is the text that is sent to an LLM as its input.

Here is how RAG works in standard steps:

1. First, load documents and split them into chunks.
2. Convert each chunk into an embedding.
3. Store the embeddings in a vector database.
4. When a user asks a question, embed the user's question.
5. Search the vector database for the most similar chunks.
6. Put those chunks and the question together in a prompt.
7. Let the LLM write the answer based on that prompt.

## Example

Let us see RAG in two real situations.

Imagine an Indian college app with a chatbot. A student asks, "What is the rule for library book returns?" The system uses RAG. It searches the college rule documents stored in a vector database. It finds the correct chunks. It adds those chunks to the student's question in a prompt. The LLM reads the text and writes the correct answer.

Imagine another case. A person asks a banking app a question about a new government scheme. The system searches the scheme documents. It finds the matching chunks and sends them to the LLM. The LLM writes the answer using only those documents.

One important limit is retrieval quality. If retrieval returns the wrong or incomplete chunks, the answer will probably be wrong or incomplete. The LLM can still misread or ignore the retrieved text. Therefore, RAG systems should be tested before use.

## Recap

- RAG stands for Retrieval-Augmented Generation.
- RAG means retrieving information, adding it to the prompt, and letting an LLM generate the answer.
- The model weights are not changed during RAG.
- RAG reduces hallucination by giving the model real source text.
- Updating a RAG system requires only updating the documents in the knowledge base.
- Retrieval quality matters most for a good answer.

## Check Yourself

1. What does the term RAG stand for?
2. Why does RAG not require retraining the model?
3. What is a chunk?
