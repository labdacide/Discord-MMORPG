import discord
import aiohttp
import asyncio
import os

async def create_wallet_code():
    async with aiohttp.ClientSession() as session:
        url = os.getenv("WEBHOOK_WALLET_ONBOARDING")
        if (url == None): return
        async with session.post(url) as resp:
            data = await resp.json()
            return data['code']

async def create_milestone_reward_claim(url, code: str):
    if (url == None): return
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={ 'code': code }) as resp:
            data = await resp.json()
            return data
