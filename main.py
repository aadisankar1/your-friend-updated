import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Replace with your bot token. You can get this from BotFather.
# It's highly recommended to use environment variables for sensitive data.
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "") # Replace "YOUR_BOT_TOKEN_HERE" with your actual bot token
BANNED_WORDS_FILE = "banned.txt"

# Set to store banned words for efficient lookup
banned_words = set()

# --- Persistence Functions for Banned Words ---
def load_banned_words():
    """Loads banned words from the specified file into the global set."""
    global banned_words
    try:
        if os.path.exists(BANNED_WORDS_FILE):
            with open(BANNED_WORDS_FILE, "r", encoding="utf-8") as f:
                # Read words, strip whitespace, convert to lowercase, and add to set
                banned_words = {word.strip().lower() for word in f if word.strip()}
            logger.info(f"Loaded {len(banned_words)} banned words from {BANNED_WORDS_FILE}.")
        else:
            # Create an empty file if it doesn't exist
            with open(BANNED_WORDS_FILE, "w", encoding="utf-8") as f:
                pass # Just create the file
            logger.info(f"Created new banned words file: {BANNED_WORDS_FILE}")
    except Exception as e:
        logger.error(f"Error loading banned words from file: {e}")
        banned_words = set() # Ensure it's an empty set on error

def save_banned_words():
    """Saves the current banned words set to the specified file."""
    try:
        with open(BANNED_WORDS_FILE, "w", encoding="utf-8") as f:
            for word in sorted(list(banned_words)): # Sort for consistent file content
                f.write(f"{word}\n")
        logger.info(f"Saved {len(banned_words)} banned words to {BANNED_WORDS_FILE}.")
    except Exception as e:
        logger.error(f"Error saving banned words to file: {e}")

# --- Helper Function: Check if user is an administrator ---
async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if the user who sent the message is an administrator in the group."""
    if not update.effective_chat or not update.effective_user:
        return False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        # Get chat member information for the user
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        # Check if the user's status is 'administrator' or 'creator'
        return chat_member.status in ['administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

# --- Command Handler: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        """
Hey, this is your friendly bot!
I am a friendly bot, made by @aadiv2bot.
No user ID is shown because of security reasons.
I'm ready!
"""
    )

# --- Command Handler: /contact ---
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provides information about the bot's creator."""
    await update.message.reply_text(
        "I am made by a genius, but his ID is hidden for good reasons. "
        "Please chat with the bot @aadiv2bot."
    )

# --- Command Handler: /append ---
async def append(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Appends a word to the banned_words list if the user is a group admin.
    Usage: /append <word>
    """
    if not update.effective_chat or not update.effective_user:
        await update.message.reply_text("This command can only be used in a chat.")
        return

    # Check if the user is an admin
    if not await is_user_admin(update, context):
        await update.message.reply_text(
            "You are not authorized to use this command. "
            "Only group administrators can add banned words."
        )
        return

    # Extract the word from the command arguments
    if not context.args:
        await update.message.reply_text("Please provide a word to append. Usage: /append <word>")
        return

    word_to_add = " ".join(context.args).strip().lower()  # Join all args in case of multi-word phrase
    if not word_to_add:
        await update.message.reply_text("The word cannot be empty. Usage: /append <word>")
        return

    if word_to_add in banned_words:
        await update.message.reply_text(f"'{word_to_add}' is already in the banned words list.")
    else:
        banned_words.add(word_to_add) # Add to set
        save_banned_words() # Save changes to file
        logger.info(f"Admin {update.effective_user.username} (ID: {update.effective_user.id}) appended '{word_to_add}' to banned words.")
        await update.message.reply_text(f"Successfully added '{word_to_add}' to the banned words list.")

# --- Command Handler: /list_banned ---
async def list_banned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all words currently in the banned_words list."""
    if not banned_words:
        await update.message.reply_text("The banned words list is currently empty.")
    else:
        banned_list_str = "\n".join([f"- {word}" for word in sorted(list(banned_words))])
        await update.message.reply_text(f"Current banned words:\n{banned_list_str}")

# --- Message Handler: word_detector ---
async def word_detector(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks if a message contains any banned words and attempts to delete it."""
    if not update.message or not update.message.text:
        return # Not a text message

    user_message = update.message.text
    user_message_lower = user_message.lower()

    for banned_word in banned_words:
        if banned_word in user_message_lower:
            try:
                # Attempt to delete the message
                await update.message.delete()
                # Inform the user that their message was removed
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Hey! Please be kind and avoid using rude words. Your message was removed."
                )
                logger.info(f"Deleted message from {update.effective_user.username} (ID: {update.effective_user.id}) containing banned word: '{banned_word}'")
                break # Stop checking after the first banned word is found and message deleted
            except Exception as e:
                logger.error(f"Error deleting message from {update.effective_user.username} (ID: {update.effective_user.id}): {e}")
                # If deletion fails (e.g., no permission, message too old), still send a warning.
                await update.message.reply_text("Hey! Please be kind and avoid using rude words.")
                break # Stop checking after attempting to warn/delete

# --- Main function to run the bot ---
def main() -> None:
    """Starts the bot."""
    # Load banned words at startup
    load_banned_words()

    # Create the Application and pass your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("contact", contact)) # Added contact command
    application.add_handler(CommandHandler("append", append))
    application.add_handler(CommandHandler("list_banned", list_banned))

    # Register message handler for word detection (checks all text messages not starting with a command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, word_detector))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(poll_interval=3)

if __name__ == "__main__":
    main()
