import os
import discord
import aiohttp
from dotenv import load_dotenv
from console_log import console_log

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def get_model_response(message: discord.Message) -> str|None:
    API_KEY = os.getenv("API_KEY")

    if not API_KEY:
        return None

    # Get nickname from message
    nick = (
            message.author.nick
            or message.author.global_name
            or message.author.name
    )

    # Remove bot mention in message
    content = message.content.replace(f"<@{client.user.id}>", "").strip()

    # Get instructions from 'instructions.txt'
    with open("instructions.txt", 'r') as f:
        instructions = f.read().strip()

    prompt = f"""
        {instructions}
        This is the message by {nick}:
        {content}
    """

    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [
            {"role": "system", "content": prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers
            ) as resp:
                if resp.status != 200:
                    console_log(f"OpenRouter error: {resp.status}")
                    return None

                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        console_log(f"Error getting message from model: {e}")
        return None

async def send_message(text: str, message: discord.Message):
    if not text:
        text = "Ups! Algo correu mal..."

    try:
        await message.reply(text, mention_author=False)

    except discord.DiscordException:
        console_log("Error sending message")
        return

@client.event
async def on_ready():
    console_log("Chat Bot ready")
    return

@client.event
async def on_message(message):
    if client.user in message.mentions and message.author != client.user:
        console_log("Bot mentioned, answering")

        response = await get_model_response(message)
        console_log("Message received, sending")
        if not response:
            console_log("Message is null")

        await send_message(response, message)
        return

def main():
    try:
        client.run(DISCORD_TOKEN)
    except Exception as e:
        console_log(str(e))

if __name__ == '__main__':
    main()
