import os
from openai import OpenAI
from dotenv import load_dotenv
import json

from AI.idea_history import recent_ideas, remember_idea

load_dotenv()


def generate_response(prompt):
    api_key = os.getenv("CHATGPT_API_KEY")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    return response.output_text


def _idea_history_prompt(app):
    history = recent_ideas(app)
    if not history:
        return "There are no previous ideas yet."

    formatted_ideas = [
        f'{index}. [{entry.get("contentType", "unknown")}] '
        f'{entry.get("idea", "")}'
        for index, entry in enumerate(history, start=1)
    ]
    return "PREVIOUS IDEAS TO AVOID:\n" + "\n".join(formatted_ideas)


def _generate_and_remember_idea(app, content_type, prompt):
    previous_ideas = {
        entry.get("idea", "").strip().casefold()
        for entry in recent_ideas(app)
    }

    idea = generate_response(prompt).strip()
    if idea.casefold() in previous_ideas:
        idea = generate_response(
            prompt
            + "\nYour last answer exactly repeated an earlier idea. "
            + "Choose a completely different scenario and creative device."
        ).strip()

    remember_idea(app, content_type, idea)
    return idea


def generate_video_idea(app):
    idea_history = _idea_history_prompt(app)
    prompt = f"""
Based on this app:

{app}

Generate one strong short-form marketing video idea.

The full video must fit within 6 seconds.

The idea must be self-contained. A viewer who has never heard of the app
must understand:
- the exact real-world situation or problem
- what the user does with the app
- how that protects or helps the user

Do not rely on vague ideas like "having proof" without explaining what is
being documented and why the viewer may need it.

Keep the idea short and concrete.

Before answering, consider several concepts with different situations, hooks,
emotions and visual devices. Return only the strongest one.

The new concept must be meaningfully different from every previous idea below.
Changing names, objects or wording does not count as a new idea. Use a different
core situation, conflict and creative hook.

{idea_history}
"""

    return _generate_and_remember_idea(app, "video", prompt)


def generate_video_script(idea, app):
    prompt = f"""
You are a highly creative TikTok/Reels ad director.

Video idea:
{idea}

App:
{app}

Turn this into a bold, memorable 6-second vertical video ad.

Be creative. Do NOT just literally visualize the idea.
Use humor, surprise, tension, satisfying visuals, dramatic reveals,
POV shots, clever transitions, unexpected situations or emotional moments
when appropriate.

PLAN THE FULL 6 SECONDS BEAT BY BEAT.

Example structure:
0.0-1.0s: immediate visual hook
1.0-3.0s: problem/action escalates
3.0-5.0s: payoff or reveal
5.0-6.0s: memorable ending

The video may include:
- narrator / voiceover
- natural dialogue
- sound effects
- music
- environmental audio
- dramatic audio transitions

Use audio deliberately to make the video more engaging.

CLARITY RULES:
- a viewer must understand the video without knowing anything about the app
- clearly establish the exact real-world situation and problem
- clearly show what the person records, saves or does with the app
- make the practical benefit obvious by the end
- do not use vague phrases like "proof when you need it" without context
- use one short, natural spoken line when visuals alone cannot explain this

VIDEO RULES:
- vertical 9:16
- approximately 6 seconds
- photorealistic
- fast, visually clear storytelling
- strong first second
- one coherent concept
- realistic camera movement and lighting
- avoid boring static shots
- avoid generic stock-ad style
- no fake app UI
- NO app logo
- NO brand logo
- NO end card
- NO outro screen
- NO product screen
- NO splash screen
- NO on-screen text
- NO captions
- NO subtitles
- NO signs with readable text
- NO labels with readable text
- NO text overlays of any kind
- if a phone is visible, its screen must not show readable UI or text
- spoken narration/dialogue is allowed
- if spoken words are used, keep them extremely short
- script maximum 1200 characters

The "script" should describe:
- exact timing
- action
- camera movement
- expressions/reactions
- audio/music/SFX
- narration/dialogue if useful

The final second must remain part of the natural scene.
Do NOT cut to a logo, title card, app screen, CTA screen, or branded ending.

Also create a short natural social media description and 3-5 hashtags.
The description must plainly explain what the app does and when it is useful.

Return ONLY valid JSON:

{{
    "script": "full timed video-generation prompt",
    "description": "short social media description",
    "hashtags": ["#tag1", "#tag2", "#tag3"]
}}
"""

    return json.loads(generate_response(prompt))


def generate_slides_idea(app):
    idea_history = _idea_history_prompt(app)
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

Before answering, consider several concepts with different situations, hooks,
emotions and story structures. Return only the strongest one.

The new concept must be meaningfully different from every previous idea below.
Changing the title or wording does not count as a new idea. Use a different core
topic, viewer problem and narrative angle.

{idea_history}
"""

    return _generate_and_remember_idea(app, "slideshow", prompt)


def generate_slides(idea, app):
    prompt = f"""
Create a complete TikTok/Reels-style IMAGE SLIDESHOW.

APP:
{app}

SLIDESHOW IDEA:
{idea}

Create between 5 and 7 slides.

The slideshow should tell one coherent mini-story.

CLARITY RULES:
- assume the viewer has never heard of the app
- by slide 2, clearly name the exact situation or problem
- explain what action the viewer should take and why it matters
- the final two slides must clearly explain what the app records or organizes
- state the practical benefit instead of vaguely saying the app "helps"
- avoid unclear pronouns, metaphors or references that need outside context
- clarity is more important than making every line extremely short

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
- ideally 6-14 words per slide
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


SOCIAL POST DATA:
- write one short natural description for the slideshow
- include 3-5 relevant hashtags
- choose one real, existing song that fits the slideshow mood
- provide the exact song title and artist; do not invent a song


Return ONLY valid JSON in exactly this structure:

{{
    "description": "short social media description",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "music": {{
        "title": "exact song title",
        "artist": "artist name"
    }},
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
