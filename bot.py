import os
import discord
import aiohttp
import sys
from dotenv import load_dotenv
from console_log import console_log

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

ENABLE_CONTEXT = False
CONTEXT_WINDOW_SIZE = 0
CONTEXT_WINDOW = []

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

    if ENABLE_CONTEXT:
        prompt = f"""
            {instructions}
            These are the {CONTEXT_WINDOW_SIZE} previous messages and answers
            in the format "User_Nickname: user_message\nModel_response":
            {CONTEXT_WINDOW}
            This is the message by {nick}:
            {content}
        """
    else:
        prompt = f"""
            {instructions}
            This is the message by {nick}:
            {content}
        """

    payload = {
        # CHANGE MODEL HERE
        "model": "x-ai/grok-4.20",
        "messages": [
            {"role": "system", "content": prompt}
        ],
        # CHANGE MAX TOKEN USAGE HERE
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
                response = data["choices"][0]["message"]["content"].strip()

                CONTEXT_WINDOW.append(f"{nick}: {content}\n{response}")

                # Cut previous messages
                if len(CONTEXT_WINDOW) > CONTEXT_WINDOW_SIZE:
                    CONTEXT_WINDOW.pop(0)

                return response

    except Exception as e:
        console_log(f"Error getting message from model: {e}")
        return None

async def send_message(text: str | None, message: discord.Message):
    if not text:
        text = "Something went wrong... Ask later."

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
    if message.author == client.user:
        return

    mentioned = client.user in message.mentions

    replied_to_bot = (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author == client.user
    )

    if mentioned or replied_to_bot:
        console_log("Bot mentioned, answering")

        response = await get_model_response(message)
        console_log("Message received, sending")
        if not response:
            console_log("Message is null")

        await send_message(response, message)
        return

def main():
    global CONTEXT_WINDOW_SIZE, ENABLE_CONTEXT

    try:
        if len(sys.argv) > 1:
            CONTEXT_WINDOW_SIZE = int(sys.argv[1])
            if CONTEXT_WINDOW_SIZE <= 0:
                raise Exception("Context window size must be greater than 0")
            ENABLE_CONTEXT = True

        if DISCORD_TOKEN is None:
            raise Exception("No Discord token provided")

        client.run(DISCORD_TOKEN)
    except ValueError:
        console_log("Wrong arguments: python3 bot.py {Context Window or Nothing if disabled}")
        return
    except Exception as e:
        console_log(str(e))

if __name__ == '__main__':
    main()
