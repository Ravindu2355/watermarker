from pyrogram import Client, filters
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ImageClip
import os
import time

# Bot API credentials
API_ID = os.getenv("apiid")
API_HASH = os.getenv("apihash")
BOT_TOKEN = os.getenv("tk")

# Initialize the bot client
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Folder for saving and processing files
TEMP_DIR = "downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

# Path to the logo image
LOGO_PATH = "logo.png"  # Provide the path to your logo image

# Throttle progress messages
def update_progress_message(client, chat_id, message_id, text, last_update_time):
    current_time = time.time()
    if current_time - last_update_time >= 10:  # Update every 10 seconds
        client.edit_message_text(chat_id, message_id, text)
        return current_time
    return last_update_time

# Function to add watermark and logo
def add_watermark(video_path, watermark_text, logo_path, output_path, progress_callback):
    # Load the video
    video = VideoFileClip(video_path)

    # Add text watermark
    watermark = TextClip(watermark_text, fontsize=30, color='white', font="Arial-Bold")
    watermark = watermark.set_pos(("right", "bottom")).set_duration(video.duration)

    # Add logo
    if os.path.exists(logo_path):
        logo = ImageClip(logo_path)
        logo = (
            logo.set_duration(video.duration)
                .resize(height=50)  # Resize the logo
                .set_pos(("left", "bottom"))  # Position the logo at the bottom-left
        )
        video_with_watermark = CompositeVideoClip([video, watermark, logo])
    else:
        video_with_watermark = CompositeVideoClip([video, watermark])

    # Export the watermarked video with progress callback
    video_with_watermark.write_videofile(output_path, codec="libx264", audio_codec="aac", progress_bar=False, verbose=False, logger=progress_callback)

    video.close()
    video_with_watermark.close()

# Function to generate thumbnail
def generate_thumbnail(video_path, thumbnail_path, timestamp=1.0):
    with VideoFileClip(video_path) as video:
        frame = video.get_frame(timestamp)
        thumbnail_clip = ImageClip(frame)
        thumbnail_clip.save_frame(thumbnail_path)
        thumbnail_clip.close()

@app.on_message(filters.video & filters.private)
async def handle_video(client, message):
    chat_id = message.chat.id
    progress_message = await message.reply_text("Starting the process...")
    last_update_time = time.time()

    try:
        # Download the video
        video = await message.download(file_name=TEMP_DIR, progress=progress_callback(client, chat_id, progress_message, "Downloading...", last_update_time))
        output_video_path = os.path.join(TEMP_DIR, f"watermarked_{os.path.basename(video)}")
        thumbnail_path = os.path.join(TEMP_DIR, f"thumbnail_{os.path.basename(video)}.jpg")

        # Add watermark and logo with progress updates
        def moviepy_progress_callback(progress):
            nonlocal last_update_time
            message_text = f"Processing video: {int(progress * 100)}% completed..."
            last_update_time = update_progress_message(client, chat_id, progress_message.message_id, message_text, last_update_time)

        watermark_text = "My Watermark"  # Change this to your desired text
        await client.edit_message_text(chat_id, progress_message.message_id, "Processing the video...")
        add_watermark(video, watermark_text, LOGO_PATH, output_video_path, moviepy_progress_callback)

        # Generate thumbnail
        await client.edit_message_text(chat_id, progress_message.message_id, "Generating thumbnail...")
        generate_thumbnail(output_video_path, thumbnail_path)

        # Upload the processed video with progress
        await client.edit_message_text(chat_id, progress_message.message_id, "Uploading the video...")
        await client.send_video(
            chat_id=chat_id,
            video=output_video_path,
            caption="Here is your watermarked video!",
            thumb=thumbnail_path,
            supports_streaming=True,
            progress=progress_callback(client, chat_id, progress_message, "Uploading...", last_update_time)
        )

        # Cleanup
        os.remove(video)
        os.remove(output_video_path)
        os.remove(thumbnail_path)
        await client.delete_messages(chat_id, progress_message.message_id)
    except Exception as e:
        await client.edit_message_text(chat_id, progress_message.message_id, f"An error occurred: {str(e)}")

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Hello! Send me a video, and I'll add a watermark and logo to it!")

# Run the bot
if __name__ == "__main__":
    app.run()
