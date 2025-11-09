import asyncio
from database import AsyncSessionLocal
from models.queue import Queue

async def init_queues():
    async with AsyncSessionLocal() as db:
        for i in range(1, 13):
            queue = Queue(
                queue_id=i,
                name=f"Черга {i}",
                is_power_on=True
            )
            db.add(queue)
        
        await db.commit()
        print("✅ Створено 12 черг")

if __name__ == "__main__":
    asyncio.run(init_queues())
