import json
import os
import discord
import aiohttp
import argparse
from dotenv import load_dotenv
from console_log import console_log

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Context related variables
ENABLE_CONTEXT = False
CONTEXT_WINDOW_SIZE = -1
CONTEXT_WINDOW = []

# Person specific info variables
# Allow personalised info (from a JSON) for different people to reduce token usage
# The info is only fetched if the person (a key) is mentioned in the message
ENABLE_PERSONALISED = False

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

    prompt = f"{instructions}"

    if ENABLE_CONTEXT:
        prompt += f"""
            These are the {CONTEXT_WINDOW_SIZE} previous messages and answers
            in the format "User_Nickname: user_message\nModel_response":
            {CONTEXT_WINDOW}
        """

    if ENABLE_PERSONALISED:
        with open("info.json", "r") as info_file:
            user_data = json.load(info_file)

        # Check who is mentioned
        matches = [key for key in user_data.keys() if key.lower() in content.lower()]

        if matches:
            prompt += "\nThis is personalized info from people mentioned, make sure to include it\n"
            for match in matches:
                prompt += f"""
                        {match} personal info:
                        {user_data[match]}
                    """

    prompt += f"""
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
        "max_tokens": 350,
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

                # Cut previous messages
                if ENABLE_CONTEXT:
                    CONTEXT_WINDOW.append(f"{nick}: {content}\n{response}")
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
    global CONTEXT_WINDOW_SIZE, ENABLE_CONTEXT, ENABLE_PERSONALISED

    parser = argparse.ArgumentParser("Discord AI Chat Bot")

    try:
        parser.add_argument("--context-window-size", type=int, default=CONTEXT_WINDOW_SIZE,
                            help="Number of messages in the chatbot context window, must include an integer as argument")
        parser.add_argument("--personalised", action="store_true",
                            help="Enabled personalised info for users fetched from a json file "
                                 "with users as keys and descriptions as values")

        args = parser.parse_args()

        if args.context_window_size != -1:
            if args.context_window_size <= 0:
                raise Exception("Context window size must be above 0")

            ENABLE_CONTEXT = True
            CONTEXT_WINDOW_SIZE = args.context_window_size

        if args.personalized:
            if not os.path.exists("info.json"):
                raise Exception("Personalised info file (info.json) not found")

            ENABLE_PERSONALISED = True

        if DISCORD_TOKEN is None:
            raise Exception("No Discord token provided")

        if not os.path.exists("instructions.txt"):
            raise Exception("Instructions file not found")

        client.run(DISCORD_TOKEN)
    except ValueError:
        console_log("Wrong arguments (leave blank if disabled): python3 bot.py {Context Window}")
        return
    except Exception as e:
        console_log(str(e))
        return

if __name__ == '__main__':
    main()
