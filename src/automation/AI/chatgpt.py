import os
import random
from openai import OpenAI
from dotenv import load_dotenv
import json

from automation.AI.idea_history import recent_ideas, remember_idea
from automation.AI.audio_history import (
    audio_was_used,
    recent_audio,
    remember_audio,
)

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

The generated story will be 15 seconds, followed by a separate 2-second branded
app card. Build a concept that uses the full 15 seconds without feeling slow.

The idea must be self-contained. A viewer who has never heard of the app
must understand:
- the exact real-world situation or problem
- what the user does with the app
- how that protects or helps the user

Do not rely on vague ideas like "having proof" without explaining what is
being documented and why the viewer may need it.

Keep the idea short and concrete. Favor a relatable pain point with an immediate
visual consequence, a clear demonstration of the app action, and a satisfying
before/after payoff.

The AI-generated footage must contain no readable text of any kind. Do not
propose captions, titles, signs, labels, logos, app UI text, or text overlays in
the concept. Separate post-production handles all visible copy and branding.

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

Turn this into a bold, memorable 15-second vertical video ad. A separate
2-second branded app card with real UI is added afterward, making the published
video approximately 17 seconds total.

Be creative. Do NOT just literally visualize the idea.
Use humor, surprise, tension, satisfying visuals, dramatic reveals,
POV shots, clever transitions, unexpected situations or emotional moments
when appropriate.

PLAN THE FULL 15 SECONDS BEAT BY BEAT.

Example structure:
0.0-1.5s: immediate visual and spoken hook
1.5-4.0s: specific problem and consequence
4.0-9.0s: person visibly uses the app to take the key action
9.0-13.0s: satisfying result / before-and-after payoff
13.0-15.0s: natural reaction that leads into the branded app card

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
- communicate the core benefit by second 5, not only at the end
- show the phone/app action clearly, but keep unreadable generated UI simple;
  the real app interface appears in the separate branded card
- make the visual story understandable without sound; post-production adds the
  only permitted text after the AI footage is generated

VIDEO RULES:
- vertical 9:16
- exactly 15 seconds before the separate 2-second branded card
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
- absolutely NO text rendered inside the generated footage
- NO captions, subtitles, titles, labels, signs, logos, watermarks, letters,
  numbers, app names, or readable phone-screen content
- do not describe any on-screen text in the timed script
- communicate the hook and benefit through action, framing, expressions, props,
  and optional spoken audio only
- NO signs with readable text
- NO labels with readable text
- if a phone is visible, its screen must not show readable UI or text
- spoken narration/dialogue is allowed
- if spoken words are used, keep them extremely short
- script maximum 2200 characters

The "script" should describe:
- exact timing
- action
- camera movement
- expressions/reactions
- audio/music/SFX
- narration/dialogue if useful

The final second must remain part of the natural scene and visually lead into
the separately added branded card. Do not generate a fake logo, fake UI, title
card, or branded end screen inside these 15 seconds.

Also create a short natural social media description and 3-5 hashtags.
The description must plainly explain what the app does and when it is useful.
Use a concrete benefit-led call to action, not a vague awareness caption.
Create two short strings as METADATA for reliable post-production rendering.
They must not appear or be requested anywhere inside the generated footage or
timed script:
- "hookText": 2-6 words stating the specific opening hook
- "benefitText": 2-6 words stating the concrete app benefit

Return ONLY valid JSON:

{{
    "script": "full timed video-generation prompt",
    "hookText": "2-6 word opening hook",
    "benefitText": "2-6 word app benefit",
    "description": "short social media description",
    "hashtags": ["#tag1", "#tag2", "#tag3"]
}}
"""

    last_error = "unknown validation error"
    for attempt in range(3):
        retry = "" if attempt == 0 else f"\nFix this problem: {last_error}."
        try:
            video_data = json.loads(generate_response(prompt + retry))
        except (json.JSONDecodeError, TypeError) as exc:
            last_error = f"invalid JSON ({exc})"
            print(f"Video-script attempt {attempt + 1} rejected: {last_error}")
            continue

        hook_words = str(video_data.get("hookText", "")).split()
        benefit_words = str(video_data.get("benefitText", "")).split()
        hashtags = video_data.get("hashtags")
        if not str(video_data.get("script", "")).strip():
            last_error = "script is missing"
        elif not 2 <= len(hook_words) <= 6:
            last_error = "hookText must contain 2-6 words"
        elif not 2 <= len(benefit_words) <= 6:
            last_error = "benefitText must contain 2-6 words"
        elif not str(video_data.get("description", "")).strip():
            last_error = "description is missing"
        elif not isinstance(hashtags, list) or not 3 <= len(hashtags) <= 5:
            last_error = "expected 3-5 hashtags"
        else:
            return video_data
        print(f"Video-script attempt {attempt + 1} rejected: {last_error}")

    raise ValueError(
        f"Could not generate a valid video script after 3 attempts: {last_error}"
    )


def generate_slides_idea(app, content_style):
    idea_history = _idea_history_prompt(app)
    prompt = f"""
You are creating a TikTok/Reels-style image slideshow for this app:

{app}

Come up with ONE strong slideshow concept.

CONTENT STYLE: {content_style}
Commit fully to this style. The concept and hook must feel native to it.

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

    return _generate_and_remember_idea(
        app, f"slideshow:{content_style}", prompt
    )


def generate_slides(idea, app, content_style, proof_filenames):
    proof_filename = (
        random.SystemRandom().choice(proof_filenames)
        if proof_filenames
        else None
    )
    solution_count = 2 if proof_filename else 3

    content_prompt = f"""
Write the slide COPY for one TikTok/Reels image slideshow.

APP:
{app}

IDEA:
{idea}

STYLE:
{content_style}

This is only the copywriting step. Python will put the slides in the correct
order and attach the images. Do not choose stage names or image-source types.

Write exactly:
- one hook that is clear in under one second and does not name the app
- one specific problem and its consequence
- exactly {solution_count} solution steps that deliver the hook's payoff
{f'- one proof caption describing what the real screenshot named {proof_filename!r} demonstrates' if proof_filename else ''}
- one natural app CTA that connects the solution back to the problem

For the hook, problem, solutions, and CTA, include a concrete 2-6 word Pinterest
query. Queries describe visible people, objects, actions, or places. They must
not request UI, screenshots, text, logos, or abstract concepts.

COPY RULES:
- assume the viewer has never heard of the app
- keep each line conversational, ideally 6-14 words
- make the practical action and benefit specific
- do not make unsupported claims
- no hashtags and no corporate language
- commit fully to the {content_style} style

Return ONLY valid JSON:
{{
  "hook": {{"text": "...", "imageQuery": "..."}},
  "problem": {{"text": "...", "imageQuery": "..."}},
  "solutions": [
    {{"text": "...", "imageQuery": "..."}}
  ],
  "proofText": "what the screenshot demonstrates",
  "cta": {{"text": "...", "imageQuery": "..."}}
}}

Return exactly {solution_count} objects in "solutions".
Set "proofText" to an empty string when no screenshot was specified.
Do not include markdown or explanations.
"""

    content = None
    last_content_error = "unknown validation error"
    for attempt in range(3):
        retry = (
            ""
            if attempt == 0
            else f"\nFix the previous response. Problem: {last_content_error}."
        )
        raw_response = generate_response(content_prompt + retry)
        try:
            candidate = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as exc:
            last_content_error = f"invalid JSON ({exc})"
            print(f"Slide-copy attempt {attempt + 1} rejected: {last_content_error}")
            continue

        required_cards = [candidate.get("hook"), candidate.get("problem")]
        solutions = candidate.get("solutions")
        required_cards.append(candidate.get("cta"))
        if not all(isinstance(card, dict) for card in required_cards):
            last_content_error = "hook, problem, or CTA is missing"
        elif not isinstance(solutions, list) or len(solutions) != solution_count:
            last_content_error = f"expected exactly {solution_count} solutions"
        elif not all(isinstance(card, dict) for card in solutions):
            last_content_error = "a solution is not an object"
        elif not all(
            str(card.get("text", "")).strip()
            and str(card.get("imageQuery", "")).strip()
            for card in required_cards + solutions
        ):
            last_content_error = "a slide is missing text or imageQuery"
        elif proof_filename and not str(candidate.get("proofText", "")).strip():
            last_content_error = "proofText is missing"
        else:
            content = candidate
            break

        print(f"Slide-copy attempt {attempt + 1} rejected: {last_content_error}")

    if content is None:
        raise ValueError(
            f"Could not generate valid slide copy after 3 attempts: {last_content_error}"
        )

    slides = [
        {
            "stage": "hook",
            "text": content["hook"]["text"],
            "imageSource": "pinterest",
            "imageQuery": content["hook"]["imageQuery"],
        },
        {
            "stage": "problem",
            "text": content["problem"]["text"],
            "imageSource": "pinterest",
            "imageQuery": content["problem"]["imageQuery"],
        },
    ]
    slides.extend(
        {
            "stage": "solution",
            "text": solution["text"],
            "imageSource": "pinterest",
            "imageQuery": solution["imageQuery"],
        }
        for solution in content["solutions"]
    )
    if proof_filename:
        slides.append(
            {
                "stage": "proof",
                "text": content["proofText"],
                "imageSource": "proof",
                "proofImage": proof_filename,
            }
        )
    slides.append(
        {
            "stage": "cta",
            "text": content["cta"]["text"],
            "imageSource": "pinterest",
            "imageQuery": content["cta"]["imageQuery"],
        }
    )

    audio_history = recent_audio(app)
    if audio_history:
        previous_audio = "\n".join(
            f'- "{entry.get("title", "")}" by {entry.get("artist", "")}'
            for entry in audio_history
        )
    else:
        previous_audio = "There is no previously used audio yet."

    slide_copy = "\n".join(f'- {slide["text"]}' for slide in slides)
    metadata_prompt = f"""
Create the SOCIAL POST METADATA for this slideshow.

APP: {app}
STYLE: {content_style}
SLIDE COPY:
{slide_copy}

Write one short, natural description and 3-5 relevant hashtags. Choose one
real, existing song that fits the mood. Give its exact title and artist.
Do not use any song in this list:
{previous_audio}

Return ONLY valid JSON:
{{
  "description": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "music": {{"title": "...", "artist": "..."}}
}}
"""

    last_metadata_error = "unknown validation error"
    for attempt in range(3):
        retry = "" if attempt == 0 else f"\nFix this problem: {last_metadata_error}."
        try:
            metadata = json.loads(generate_response(metadata_prompt + retry))
        except (json.JSONDecodeError, TypeError) as exc:
            last_metadata_error = f"invalid JSON ({exc})"
            print(f"Metadata attempt {attempt + 1} rejected: {last_metadata_error}")
            continue
        music = metadata.get("music", {})
        title = str(music.get("title", "")).strip()
        artist = str(music.get("artist", "")).strip()
        description = str(metadata.get("description", "")).strip()
        hashtags = metadata.get("hashtags")
        if not description:
            last_metadata_error = "description is missing"
        elif not isinstance(hashtags, list) or not 3 <= len(hashtags) <= 5:
            last_metadata_error = "expected 3-5 hashtags"
        elif not all(isinstance(tag, str) and tag.startswith("#") for tag in hashtags):
            last_metadata_error = "every hashtag must start with #"
        elif not title or not artist:
            last_metadata_error = "music title or artist is missing"
        elif audio_was_used(app, title, artist):
            last_metadata_error = f'"{title}" by {artist} was already used'
        else:
            remember_audio(app, title, artist)
            return {
                "description": description,
                "hashtags": hashtags,
                "music": {"title": title, "artist": artist},
                "slides": slides,
            }

        print(f"Metadata attempt {attempt + 1} rejected: {last_metadata_error}")

    raise ValueError(
        f"Could not generate valid social metadata after 3 attempts: "
        f"{last_metadata_error}"
    )
