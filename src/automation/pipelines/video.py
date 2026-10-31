from automation.AI.chatgpt import generate_video_idea, generate_video_script
from automation.AI.videogeneration import generate_video
from automation.utils import upload_with_browser


def run_video_pipeline(playwright, app):
    print(f"Creating a video for {app['appName']}...")
    video_idea = generate_video_idea(app)
    video_data = generate_video_script(video_idea, app)
    video_path = generate_video(video_data, app)

    upload_with_browser(
        playwright,
        app,
        lambda tiktok: tiktok.upload_video(
            video_path,
            video_data["description"],
            video_data["hashtags"],
        ),
    )
