## Tech Stack

| **Layer**      | **Tool**                   | **Why**                                        |
|----------------|----------------------------|------------------------------------------------|
| LLM            | Groq (Llama 3.1 70B)       | Free tier, 10-20x faster than GPU inference    |
| Embeddings     | Voyage AI voyage-3-lite    | 200M tokens/month free, Anthropic recommended  |
| Vector store   | Supabase pgvector          | PostgreSQL extension — no extra service needed |
| Semantic cache | pgvector similarity search | Reduces LLM calls for repeated questions       |
| API            | FastAPI                    | Async, Pydantic validation, streaming support  |
| Database       | Supabase PostgreSQL        | Free tier, excellent dashboard                 |
| Config         | pydantic-settings          | Type-safe, env var override                    |
| Logging        | Loguru                     | Structured, stdlib interception                |