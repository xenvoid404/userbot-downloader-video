from pyrogram import Client, filters
import os
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logging.getLogger("pyrogram").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


def humanbytes(size):
    """Mengubah byte menjadi format yang mudah dibaca"""
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    powers_dict = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {powers_dict[n]}"


def create_progress_callback(filename):
    """
    Membuat fungsi progress callback yang stateful dan unik
    untuk setiap download.
    """
    last_log_time = time.time()
    LOG_INTERVAL = 30

    async def progress_callback(current, total):
        nonlocal last_log_time
        now = time.time()

        if (now - last_log_time > LOG_INTERVAL) or (current == total):
            percentage = (current / total) * 100
            current_size = humanbytes(current)
            total_size = humanbytes(total)

            log.info(
                f"Downloading {filename}: {current_size} / {total_size} ({percentage:.1f}%)"
            )

            last_log_time = now

    return progress_callback


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

    progress_for_this_file = create_progress_callback(filename)

    log.info(f"Mulai download: {filename} (Total: {humanbytes(media.file_size)})")

    try:
        await client.download_media(
            replied,
            file_name=save_path,
            progress=progress_for_this_file,
        )

        log.info(f"Video tersimpan: {save_path} (Download 100% selesai)")

    except Exception as e:
        log.exception(f"Gagal download file {filename}.")


log.info("Userbot berjalan...")
app.run()
