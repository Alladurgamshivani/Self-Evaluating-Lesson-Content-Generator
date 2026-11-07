# Introduction to RAG: Teaching an Artificial Intelligence (AI) System to Look Things Up

## Hook

Imagine you ask a chatbot, "What is the last date to pay my college fees?" A chatbot is a program you can talk to. It answers very fast. But the date is wrong. It never saw your college notice. It just made a guess that sounded sure.

Wrong answers like this are a big problem. RAG is one way to fix it. By the end of this lesson, you will know what RAG is. You will know why people use it. You will also see how it works, step by step.

## What Is It?

RAG stands for Retrieval-Augmented Generation. The name looks hard, but the idea is simple. Let us break it into three words.

- **Retrieval** means finding. The system finds the right information.
- **Augmented** means added. The system adds that information to your question.
- **Generation** means writing. The AI writes the answer.

So RAG is a way to let an AI look up facts before it answers. Think of an open-book exam. In a normal exam, you answer from memory. In an open-book exam, you can open the book and check. RAG gives the AI an open book.

Now let us meet the AI itself. An LLM is a computer program that reads and writes human language. LLM is short for Large Language Model. ChatGPT, Gemini and Claude are examples. An LLM learns from huge amounts of text. But it only knows what was in that text. It does not know your private files. It does not know today's news.

## Why It Matters

An LLM has three common problems. RAG helps with all three.

1. **Old knowledge.** An LLM stops learning at some date. It can miss new rules or new prices.
2. **No private data.** It has not read your college notices or your company files.
3. **Hallucination.** Hallucination means the AI makes up an answer that sounds true but is false.

With RAG, the AI reads the right page first. Then it answers from that page. This gives three benefits. Answers are more correct. Information stays up to date, because you only change the documents. And the AI can show its source, so you can check it.

RAG is usually cheaper and faster than training a model again with new data. Fine-tuning means teaching an already trained model using additional examples. With RAG, you can update the documents in its knowledge base without changing the model itself.
 You do not need to retrain the model.

## How It Works

RAG has two phases. First, we prepare the documents. Then, we answer questions.

### Phase 1: Prepare the documents (done once)

1. **Collect.** Gather your documents. These can be files in Portable Document Format, web pages or notices.
2. **Split.** Cut each document into small pieces. Each piece is called a chunk. A chunk is a few paragraphs long.
3. **Embed.** Turn each chunk into a list of numbers. This list is called an embedding. Chunks with similar meaning get similar numbers. Think of map coordinates. Two nearby places have close coordinates. Two chunks about the same topic have close numbers.
4. **Store.** Save all the embeddings in a vector database. A vector database is a special store. It can quickly find numbers that are close to each other.

### Phase 2: Answer a question (done every time)

1. **Ask.** The user types a question.
2. **Embed the question.** The question is also turned into numbers.
3. **Search.** The vector database finds the chunks closest to the question. These are the most useful pieces.
4. **Build the prompt.** A prompt is the text we send to the LLM. We put the chunks and the question together in one prompt.
5. **Generate.** The LLM reads the prompt. It writes an answer using those chunks.

The model itself does not change during this process. RAG does not retrain the model. It only changes what the model reads before it answers.

## Example

Let us see RAG in two real situations.

**Example 1: A college helpdesk bot.** A student asks, "Can I write the exam with low attendance?" The college has a rule book in Portable Document Format (PDF) form. First, the rule book is split into chunks and stored. Then the question is turned into numbers. The system finds the chunk about attendance rules. The LLM reads that chunk and explains the rule in simple words. The answer comes from the real rule book, not from a guess.

**Example 2: A scholarship scheme helper.** A student asks, "Can I apply for this government scholarship?" The helper searches the official scheme documents. It finds the pages about who can apply. The LLM then explains the rules in easy words. When the rules change, you only update the documents. You do not need to train the AI again.

One warning is important. RAG is not magic. If the search finds the wrong chunk, the answer will be wrong too. That is why people must test a RAG system before they trust it.

## Recap

- RAG lets an AI look up facts before it answers.
- First, documents are split into chunks and saved as numbers.
- Then, the best chunks are found and added to the question.
- The AI writes its answer from those chunks.
- RAG helps with old knowledge, private data and made-up answers.
- If the search finds the wrong chunks, the answer will be wrong too.

## Check Yourself

1. What do the three words in RAG mean?
2. Why is RAG cheaper than training the model again?
3. A student asks about a new exam date. Which step in RAG finds the right notice?
