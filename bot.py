import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Voice
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
    MessageHandler,
    CommandHandler,
)
import asyncio
import telegram.ext.filters as filters
from aiAnswer import generateAnswer
from whisper import generateAudio, generateTranscribe
import os
import dotenv

import requests
import json

dotenv.load_dotenv()

TOKEN_TELEGRAM = os.getenv("TG_TOKEN")
# Constants
certification = "<b>Made with ❤️ by HighTech</b>"
helpText = f"""
This is a simple telegram bot.

<b>Commands:</b>\n

🔍 /ask: Get instant answers to your equipment and project questions.\n
🎬 /voice: Get voice responses to your queries with clear audio.\n
📝 /help: Unsure what to do? Use the /help command to see a list of available commands.\n

<b>How to Use:</b>\n

<b>For Equipment Recommendations:</b> Simply use /ask followed by your query\n
e.g., /ask what's your name?\n
<b>For Voice Queries:</b> Activate voice responses with /voice followed by your question\n
e.g., /voice what's your role?\n
<b>For General Assistance:</b> Need guidance? Type /help to see how I can assist you further.\n

"""
homepageBtn = InlineKeyboardButton(
    text="🌎Website", url="https://telegram-miniapp-three.vercel.app/"
)
docsBtn = InlineKeyboardButton(text="📜Help", callback_data="docs Btn")
keyboard_markup = InlineKeyboardMarkup(
    [
        [homepageBtn, docsBtn],  # This is a row with two buttons
    ]
)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def get_gpt4_response(prompt):
    answer = generateAnswer(prompt)
    return f"{answer}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userName = update.message.chat.username
    userId = str(update.message.chat.id)
    storage_file_path = "thread_storage.json"
    # Initialize an empty dictionary to store threadIds
    thread_ids = {}
    # Check if the storage file exists and read the threadIds if it does
    if os.path.exists(storage_file_path):
        with open(storage_file_path, "r") as file:
            thread_ids = json.load(file)
    else:
        with open(storage_file_path, "w") as file:
            json.dump(thread_ids, file)
    all_keys = list(thread_ids.keys())
    # Check if the specific user_id exists in the dictionary
    if userId in all_keys:
        pass
    else:
        thread_ids[userId] = userName
        # Save the updated dictionary to the storage file
        with open(storage_file_path, "w") as file:
            json.dump(thread_ids, file)
    answer = f"""
🚀 <b>Welcome to @{userName} !</b>\n
{helpText}
"""

    response_text = f"{answer}\n{certification}"
    await update.message.reply_html(response_text, reply_markup=keyboard_markup)


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.removeprefix("/ask").strip()

    if user_message != "":
        thinking_message = await update.message.reply_text("🤖 typing...")
        # Await the response from GPT-4
        answer = await get_gpt4_response(user_message)
        response_text = f"{answer}\n\n{certification}"
        await thinking_message.edit_text(
            text=response_text, reply_markup=keyboard_markup, parse_mode=ParseMode.HTML
        )
    else:
        answer = """
<b>🪫 Prompt is empty. Please provide a prompt.</b>\n
for example: <code>/ask What's your name?</code>
"""
        response_text = f"{answer}\n\n{certification}"

        await update.message.reply_html(response_text, reply_markup=keyboard_markup)


async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.removeprefix("/voice").strip()

    if user_message != "":
        thinking_message = await update.message.reply_text("🤖 typing...")
        ## Generate a response using GPT-4
        response_text = await get_gpt4_response(user_message)
        audioPath = generateAudio(response_text)
        answer = "Gpt Answer"

        response_text = f"{answer}\n\n{certification}"
        #
        await context.bot.delete_message(
            chat_id=thinking_message.chat_id, message_id=thinking_message.message_id
        )
        # Create an InputMediaAudio object with the audio file
        await update.message.reply_audio(f"{audioPath}", reply_markup=keyboard_markup)
        # Remove the audio file after sending
        try:
            os.remove(audioPath)
            # print(f"Audio file {audioPath} has been removed.")
        except FileNotFoundError:
            print(f"Audio file {audioPath} not found.")
        except Exception as e:
            print(f"Error removing audio file {audioPath}: {e}")
    else:
        answer = """
<b>🪫 Prompt is empty. Please provide a prompt.</b>\n
For example: <code>/voice What's your role?</code>
"""
        response_text = f"{answer}\n\n{certification}"
        await update.message.reply_html(response_text, reply_markup=keyboard_markup)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = helpText
    response_text = f"{answer}\n{certification}"
    await update.message.reply_html(response_text, reply_markup=keyboard_markup)


async def helpBtn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the button click."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button click
    # Extract the callback data from the clicked button
    callback_data = query.data
    answer = helpText
    response_text = f"{answer}\n{certification}"
    await query.message.reply_html(response_text, reply_markup=keyboard_markup)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_path = "userVoiceMessage.mp3"
    voiceOver = ""
    # Check if the message has a voice attribute
    if update.message.voice:
        thinking_message = await update.message.reply_text("🤖 typing...")
        voice_message = update.message.voice
        # Get the file ID of the voice message
        file_id = voice_message.file_id
        print(f"Received voice message with file ID: {file_id}")

        # Get the File object
        file = await context.bot.get_file(file_id)
        file_path = file.file_path
        print(f"File path: {file_path}")
        response = requests.get(file_path)
        # Send a GET request to the URL
        # Check if the request was successful
        if response.status_code == 200:
            # Specify the path where you want to save the file
            with open(save_path, "wb") as file:
                file.write(response.content)
            print(f"Audio file downloaded and saved to: {save_path}")
        else:
            print("Failed to download the file.")
            # Send a reply to the user

        try:
            userMessage = generateTranscribe(save_path)
            voiceOver = generateAnswer(userMessage)
            os.remove(save_path)
            print(f"Audio file {save_path} has been removed.")
        except FileNotFoundError:
            print(f"Audio file {save_path} not found.")
            pass
        except Exception as e:
            print(f"Error removing audio file {save_path}: {e}")
            pass

        audioPath = generateAudio(voiceOver)
        await context.bot.delete_message(
            chat_id=thinking_message.chat_id, message_id=thinking_message.message_id
        )
        await update.message.reply_audio(f"{audioPath}", reply_markup=keyboard_markup)

    else:
        await update.message.reply_text("This is not a voice message.")


def main() -> None:
    """Run the bot."""
    # We use persistence to demonstrate how buttons can still work after the bot was restarted
    persistence = PicklePersistence(filepath="arbitrarycallbackdatabot")
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token(TOKEN_TELEGRAM)
        .persistence(persistence)
        .arbitrary_callback_data(True)
        .build()
    )

    application.add_handler(
        MessageHandler(filters._Voice and ~filters.COMMAND, handle_voice)
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ask", ask))
    application.add_handler(CommandHandler("voice", voice))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CallbackQueryHandler(helpBtn))

    # Run the bot until the user presses Ctrl-C
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
