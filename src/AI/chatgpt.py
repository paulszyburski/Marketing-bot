import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()


def generate_response(prompt):
    api_key = os.getenv("CHATGPT_API_KEY")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    return response.output_text


def generate_video_idea(app):
    prompt = f"""
Based on this app:

{app}

Generate one strong short-form marketing video idea.

The full video must fit within 6 seconds.

Keep the idea short and concrete.
"""

    return generate_response(prompt)


def generate_video_script(idea, app):
    prompt = f"""
Based on this video idea:

{idea}

Additional information about the app:

{app}

Generate a prompt for a video-generation AI.

Requirements:
- exactly one simple coherent scene
- approximately 6 seconds
- vertical short-form video
- photorealistic
- visually understandable immediately
- no captions
- no subtitles
- no logos
- no readable text
- no fake app UI
- maximum 1200 characters

Return ONLY the video-generation prompt.
"""

    return generate_response(prompt)


def generate_slides_idea(app):
    prompt = f"""
You are creating a TikTok/Reels-style image slideshow for this app:

{app}

Come up with ONE strong slideshow concept.

The slideshow should NOT feel like an advertisement at the beginning.

Use this structure:

1. Start with a very strong hook that stops scrolling.
2. Give useful, interesting or relatable information.
3. Build curiosity from slide to slide.
4. Naturally connect the topic to the problem the app solves.
5. Only near the end introduce the app as the solution.

HOOK RULES:
- the hook should be understandable in less than 1 second
- usually 4-10 words
- focus on the viewer, not the app
- create curiosity or an information gap
- do not reveal the whole answer immediately
- avoid generic hooks like "5 tips for..."
- avoid fake clickbait like "THIS CHANGES EVERYTHING"
- make the viewer want to swipe to slide 2

Return only a short description of the slideshow concept.
"""

    return generate_response(prompt)


def generate_slides(idea, app):
    prompt = f"""
Create a complete TikTok/Reels-style IMAGE SLIDESHOW.

APP:
{app}

SLIDESHOW IDEA:
{idea}

Create between 5 and 7 slides.

The slideshow should tell one coherent mini-story.

STRUCTURE:

SLIDE 1 — HOOK
- strongest slide
- immediately understandable
- approximately 4-10 words
- create curiosity, tension, surprise, pain or a strong promise
- focus on the viewer
- do NOT mention the app
- do NOT give away the full answer
- make the viewer want to swipe

SLIDES 2-4/5 — PAYOFF
- deliver the information promised by the hook
- each slide should contain ONE simple idea
- keep text short
- each slide should naturally lead into the next
- provide actual value rather than filler

SECOND-LAST SLIDE — BRIDGE
- connect the content naturally to the problem the app solves
- still should not feel like an aggressive advertisement

LAST SLIDE — APP / CTA
- introduce the app naturally
- explain why it helps
- use a short CTA
- do not make exaggerated or unsupported claims


TEXT RULES:
- use short conversational language
- write like native short-form social content
- avoid corporate marketing language
- ideally under 12 words per slide
- text must work as large centered text over a photo
- no hashtags
- no emojis unless they genuinely improve the slide


IMAGE QUERY RULES:
Each slide needs an "imageQuery" used to search Pinterest.

The query should:
- describe what should VISUALLY appear in the photo
- be approximately 2-6 words
- be concrete and searchable
- prefer people, actions, objects and environments
- match the emotional meaning of the slide
- NOT simply repeat the slide text
- NOT contain abstract ideas
- NOT request text in the image
- NOT request app screenshots or UI

EXAMPLE:

Bad:
"text": "You're training hard but not growing"
"imageQuery": "training hard not growing"

Good:
"text": "You're training hard but not growing"
"imageQuery": "frustrated man gym bench"


Return ONLY valid JSON in exactly this structure:

{{
    "slides": [
        {{
            "text": "slide text",
            "imageQuery": "Pinterest search query"
        }},
        {{
            "text": "slide text",
            "imageQuery": "Pinterest search query"
        }}
    ]
}}

There MUST be between 5 and 7 objects inside "slides".
Do not include markdown.
Do not include ```json.
Do not include explanations outside the JSON.
"""

    slides = generate_response(prompt)

    return json.loads(slides)