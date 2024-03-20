import asyncio
from contextlib import asynccontextmanager

class LifecycleManager:
    def __init__(self):
        self.resources = []

    @asynccontextmanager
    async def lifecycle(self, resource):
        # Setup logic (e.g., connecting to a database)
        await resource.setup()
        try:
            yield resource
        finally:
            # Teardown logic (e.g., closing database connections)
            await resource.teardown()

class AsyncResource:
    async def setup(self):
        print("Resource setup")
        # Simulate a setup task, such as connecting to a database
        await asyncio.sleep(1)

    async def teardown(self):
        print("Resource teardown")
        # Simulate a teardown task, such as closing a database connection
        await asyncio.sleep(1)

    async def use(self):
        print("Using resource")
        # Simulate using the resource
        await asyncio.sleep(1)

async def main():
    manager = LifecycleManager()
    resource = AsyncResource()

    async with manager.lifecycle(resource):
        await resource.use()

if __name__ == "__main__":
    asyncio.run(main())
