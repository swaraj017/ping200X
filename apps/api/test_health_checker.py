import asyncio

from api.services.health_checker import check_url

async def main():
    result=await check_url("https://example.com")
    print(result)

asyncio.run(main())