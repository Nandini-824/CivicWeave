import asyncio
from app.ai.embeddings import generate_embedding


async def main():
    text = "A large pothole near the college gate."

    try:
        embedding = await generate_embedding(text)

        print("Gemini connection successful!")
        print("Embedding dimensions:", len(embedding))
        print("Sample values:", embedding[:5])

    except Exception as error:
        print("Gemini test failed:", error)


if __name__ == "__main__":
    asyncio.run(main())