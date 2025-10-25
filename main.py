from pyrogram import Client, filters
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logging.getLogger("pyrogram").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


# --- Kredensial & Setup ---
API_ID = 0
API_HASH = "what?"
SESSION = "userbot_session"

DOWNLOAD_DIR = "videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client(SESSION, api_id=API_ID, api_hash=API_HASH)


@app.on_message(filters.me & filters.command("download"))
async def download_replied_video(client, message):
    replied = message.reply_to_message

    if not replied:
        log.warning("Perintah /download digunakan tanpa me-reply.")
        return

    media = replied.video or replied.document or replied.animation
    if not media:
        log.warning("Reply /download bukan ke video/dokumen/animasi.")
        return

    command_args = message.command[1:]

    if not command_args:
        log.warning("Perintah /download dipanggil tanpa nama file.")
        return

    filename_base = " ".join(command_args)

    original_extension = ""
    if media.file_name and "." in media.file_name:
        original_extension = "." + media.file_name.rsplit(".", 1)[-1]
    else:
        original_extension = ".mp4"

    if filename_base.endswith(original_extension):
        filename = filename_base
    else:
        filename = f"{filename_base}{original_extension}"

    save_path = os.path.join(DOWNLOAD_DIR, filename)

    log.info(f"Mulai download: {filename}")

    try:
        await client.download_media(replied, file_name=save_path)
        log.info(f"Video tersimpan: {save_path}")

    except Exception as e:
        log.exception(f"Gagal download file {filename}.")


log.info("Userbot berjalan...")
app.run()
