from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import os
import uvicorn

from sentence_transformers import SentenceTransformer
from pgvector.asyncpg import register_vector
import asyncpg
from database_config import ASYNCPG_DATABASE_CONFIG

# Initialize FastAPI app
app = FastAPI()

# Define input and output models for the API
class SearchRequest(BaseModel):
    search_input: str
    similarity_threshold: float = 0.1
    num_matches: int = 10
    min_price: int
    max_price: int

class SearchResult(BaseModel):
    name: str
    description: str
    original_price: float


# Load the SentenceTransformer model globally
embeddings_service = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# API Endpoint for Vector Search
@app.post("/search/", response_model=list[SearchResult])
async def search_games(request: SearchRequest):
    """
    Handles the API request to search for similar games.
    """

    # Encode the query into a vector
    qe = embeddings_service.encode(request.search_input).tolist()  # qe = Query Embedding

    # Connect to the database
    conn = await asyncpg.connect(**ASYNCPG_DATABASE_CONFIG)

    # Map the PostgreSQL vector type to a specific Python type (e.g. list)
    await register_vector(conn)

    try:
        # Perform the query
        results = await conn.fetch(
            """
            WITH vector_matches AS (
                SELECT name, 1 - (embedding <=> $1) AS similarity
                FROM steam
                WHERE 1 - (embedding <=> $1) > $2
                ORDER BY similarity DESC
                LIMIT $3
            )
            SELECT name, original_price, description FROM steam
            WHERE name IN (SELECT name FROM vector_matches)
            AND original_price >= $4 AND original_price <= $5
            """,
            qe,
            request.similarity_threshold,
            request.num_matches,
            request.min_price,
            request.max_price,
        )

        # Check if results exist
        if not results:
            raise HTTPException(status_code=404, detail="Did not find any results. Adjust the query parameters.")

        # Format the results
        matches = [
            {
                "name": r["name"],
                "description": r["description"],
                "original_price": r["original_price"],
            }
            for r in results
        ]

    finally:
        await conn.close()

    return matches


if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 8080))  # Default to 8080 if PORT is not set
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
