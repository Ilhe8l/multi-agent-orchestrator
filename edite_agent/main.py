import asyncio
from graph import get_graph

async def main():
    await get_graph()

if __name__ == "__main__":
    asyncio.run(main())