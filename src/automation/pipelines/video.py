from automation.AI.chatgpt import generate_video_idea, generate_video_script
from automation.AI.videogeneration import generate_video
from automation.montage.video import append_advertising_image
from automation.utils import upload_to_socials


def run_video_pipeline(playwright, app):
    print(f"Creating a video for {app['appName']}...")
    video_idea = generate_video_idea(app)
    video_data = generate_video_script(video_idea, app)
    video_path = generate_video(video_data, app)

    published_video = append_advertising_image(
        video_path,
        app["advertisingImage"],
        text_overlays=[
            (video_data.get("hookText"), 0.0, 2.8),
            (video_data.get("benefitText"), 6.0, 10.5),
        ],
    )

    upload_to_socials(
        playwright,
        app,
        lambda tiktok: tiktok.upload_video(
            published_video,
            video_data["description"],
            video_data["hashtags"],
        ),
        lambda youtube: youtube.upload_video(
            published_video,
            video_data["description"],
            video_data["hashtags"],
        ),
    )
