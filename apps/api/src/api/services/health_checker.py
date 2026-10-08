import httpx

async def check_url(url:str):
    #check async http client to api can make non blocking reqs
    async with httpx.AsyncClient() as client:
        #send a get request to target url
        response= await client.get(url)

        return {
            "status":"UP",
            "status_code":response.status_code,
        }