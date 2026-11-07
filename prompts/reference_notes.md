# Reference notes: Retrieval-Augmented Generation (RAG)

These are the verified facts the lesson is checked against ("grounding").
The generator may use them. The evaluator treats them as the source of truth.
Sources: Lewis et al. 2020 ("Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"),
LangChain RAG docs, Pinecone Learning Center, Hugging Face docs.

If you teach a different topic, replace this file with verified notes for that topic.

## Definition
- R1. RAG stands for Retrieval-Augmented Generation. The term was introduced in a 2020 paper by Lewis et al. (Facebook AI Research and collaborators).
- R2. RAG means: retrieve relevant information from an external knowledge source, add it to the prompt, then let a large language model (LLM) generate the answer using that information.
- R3. In RAG the model's weights are NOT changed. RAG is not training and not fine-tuning. It changes only the input (the prompt) that the model sees.

## Why it matters
- R4. An LLM only knows what was in its training data, which stops at a cutoff date. It does not know newer events.
- R5. An LLM has not seen a person's or company's private documents unless they are given to it.
- R6. Hallucination means an LLM produces text that sounds confident but is false or made up. RAG reduces hallucination by giving the model real source text to answer from. It does not remove hallucination completely.
- R7. To update a RAG system's knowledge, you update the documents in the knowledge base. You do not need to retrain the model. This is usually cheaper and faster than retraining or fine-tuning.
- R8. RAG can show which source passages were used, so users can verify the answer.

## How it works (standard pipeline)
- R9. Indexing (done ahead of time): load documents, split them into chunks, convert each chunk into an embedding, and store the embeddings in a vector database (vector store).
- R10. A chunk is a small piece of a document (for example a few paragraphs).
- R11. An embedding is a list of numbers (a vector) that represents the meaning of a piece of text. Texts with similar meaning have embeddings that are close to each other.
- R12. A vector database stores embeddings and can quickly find the ones most similar to a query embedding (similarity search).
- R13. Query time: embed the user's question, search the vector database for the most similar chunks (retrieval), put those chunks and the question together in a prompt (augmentation), and let the LLM write the answer (generation).
- R14. A prompt is the text that is sent to an LLM as its input.

## Limits
- R15. If retrieval returns the wrong or incomplete chunks, the answer will probably be wrong or incomplete. Retrieval quality matters most.
- R16. Chunk size matters: chunks that are too small lose context, chunks that are too large add noise and cost more.
- R17. The LLM can still misread or ignore the retrieved text, so RAG systems should be tested (evaluated) before use.
- R18. RAG is not the same as web search, although both fetch information. RAG usually searches a chosen set of documents.
