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


VAGUE_MARKETING_PHRASES = (
    "game changer",
    "changes everything",
    "next level",
    "peace of mind",
    "protect what matters",
    "never worry again",
    "solution you need",
    "easier than ever",
    "when it matters",
    "stay organized",
    "take control",
    "made simple",
    "work smarter",
    "you need this",
    "thank me later",
    "unlock",
    "empower",
    "seamless",
    "revolutionize",
    "betray you",
    "is lying",
    "hiding there",
)


def _short_copy_error(text, label, minimum=2, maximum=10):
    """Return a reason when short-form copy is too vague or too long."""
    normalized = " ".join(str(text).split())
    word_count = len(normalized.split())
    if not minimum <= word_count <= maximum:
        return f"{label} must contain {minimum}-{maximum} words"
    lowered = normalized.casefold()
    vague_phrase = next(
        (phrase for phrase in VAGUE_MARKETING_PHRASES if phrase in lowered),
        None,
    )
    if vague_phrase:
        return f'{label} uses vague marketing phrase "{vague_phrase}"'
    return None


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

COPY STYLE:
- use extremely simple everyday language; a 12-year-old should get it instantly
- be blunt, direct, emotionally charged and curiosity-heavy
- write like high-retention TikTok "slop," not a polished brand campaign
- hook a specific fear, mistake, annoyance, embarrassing moment or desired result
- make every line concrete enough that it could not describe 100 unrelated apps
- fragments and punchy spoken language are good; corporate copy is forbidden
- provocative is good, but never invent facts, guarantees or fake urgency

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
- "hookText": 4-8 blunt words naming the specific pain or surprising mistake
- "benefitText": 4-8 blunt words naming the exact app action or result
- both must make sense with no context and use simple everyday words
- banned filler includes: game changer, peace of mind, stay organized, take
  control, when it matters, made simple, unlock, seamless, and next level

Return ONLY valid JSON:

{{
    "script": "full timed video-generation prompt",
    "hookText": "4-8 word opening hook",
    "benefitText": "4-8 word app benefit",
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

        hook_text = str(video_data.get("hookText", "")).strip()
        benefit_text = str(video_data.get("benefitText", "")).strip()
        hook_error = _short_copy_error(hook_text, "hookText", 4, 8)
        benefit_error = _short_copy_error(benefit_text, "benefitText", 4, 8)
        hashtags = video_data.get("hashtags")
        if not str(video_data.get("script", "")).strip():
            last_error = "script is missing"
        elif hook_error:
            last_error = hook_error
        elif benefit_error:
            last_error = benefit_error
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

The slideshow must feel like native, high-retention TikTok content—not a
polished advertisement. Clarity matters more than sounding clever. The viewer
must understand the exact situation on slide 1 and what the app does by the
first solution slide.

Use this structure:

1. Start with a very strong hook that stops scrolling.
2. State the specific painful consequence in a complete thought.
3. Build curiosity with concrete information, not vague teasing.
4. Name the app in solution 1 and show the exact action it enables.
5. Name the app clearly in the final CTA.

HOOK RULES:
- the hook should be understandable in less than 1 second
- 6-11 words: enough context to understand it immediately
- focus on the viewer, not the app
- create curiosity using a specific mistake, fear, cost or desired result
- do not reveal the whole answer immediately
- avoid generic hooks like "5 tips for..."
- sound blunt and provocative, but never invent facts or guarantees
- make the viewer want to swipe to slide 2

VOICE RULES:
- use words a 12-year-old understands immediately
- write like effective TikTok "slop": direct, dramatic, casual and easy to scan
- one complete, natural thought per line; do not write cryptic fragments
- no poetic language, soft brand language, jargon or corporate polish
- do not use metaphors like "your scan betrays you" or "your food is lying"
- provocative must come from a real consequence, not mysterious wording
- never use filler such as "peace of mind," "game changer," "take control,"
  "when it matters," "stay organized," "made simple" or "next level"
- if a line could advertise 100 unrelated apps, it is too vague

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


def generate_and_select_hook(idea, app, content_style):
    """Generate several hooks, then use a separate pass to select the best."""
    generation_prompt = f"""
Generate exactly 6 genuinely different opening hooks for a short-form image
slideshow.

APP:
{app}

CONCEPT:
{idea}

STYLE: {content_style}

Each candidate must:
- contain 6-11 words
- make the exact real-world situation clear with no prior context
- use simple, natural language a 12-year-old understands
- create curiosity through a specific consequence, mistake, fear or result
- be provocative because the situation is strong, not because wording is vague
- avoid naming the app; the first solution slide introduces it
- avoid cryptic metaphors, corporate language, fake urgency and guarantees
- use a concrete 2-6 word image query showing the exact situation

The six hooks must use meaningfully different angles, not paraphrases.

Return ONLY valid JSON:
{{
  "hooks": [
    {{"text": "...", "imageQuery": "..."}}
  ]
}}
"""

    candidates = None
    last_error = "unknown hook-generation error"
    for attempt in range(3):
        retry = "" if attempt == 0 else f"\nFix this problem: {last_error}."
        try:
            response = json.loads(generate_response(generation_prompt + retry))
            hooks = response.get("hooks")
        except (json.JSONDecodeError, TypeError) as exc:
            last_error = f"invalid JSON ({exc})"
            continue
        if not isinstance(hooks, list) or len(hooks) != 6:
            last_error = "expected exactly 6 hooks"
            continue
        if not all(
            isinstance(hook, dict)
            and str(hook.get("text", "")).strip()
            and str(hook.get("imageQuery", "")).strip()
            for hook in hooks
        ):
            last_error = "every hook needs text and imageQuery"
            continue
        errors = [
            _short_copy_error(hook["text"], f"hook {index}", 6, 11)
            for index, hook in enumerate(hooks, start=1)
        ]
        if any(errors):
            last_error = next(error for error in errors if error)
            continue
        if len({hook["text"].strip().casefold() for hook in hooks}) != 6:
            last_error = "hook candidates must be unique"
            continue
        candidates = hooks
        break

    if candidates is None:
        raise ValueError(f"Could not generate hook candidates: {last_error}")

    judging_prompt = f"""
Act as a ruthless short-form retention editor. Select the single strongest hook
for this app and concept.

APP: {app['appName']} — {app.get('appDescription', '')}
CONCEPT: {idea}
CANDIDATES:
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Score each candidate from 1-10 on:
1. instant clarity with no context
2. specificity of the situation and consequence
3. emotional or curiosity pull
4. how well the proposed image proves the words
5. how naturally the next slide can introduce the app

Reject clever-sounding ambiguity. Clarity outranks shock value. Return ONLY
valid JSON with the 1-based winning index and a short reason:
{{"winner": 1, "reason": "..."}}
"""
    try:
        decision = json.loads(generate_response(judging_prompt))
        winner = int(decision["winner"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not score hook candidates: {exc}") from exc
    if not 1 <= winner <= len(candidates):
        raise ValueError(f"Hook winner index is out of range: {winner}")

    selected = candidates[winner - 1]
    print(f"Selected hook {winner}/6: {selected['text']}")
    return selected


def generate_slides(idea, app, content_style, proof_filenames):
    proof_filename = (
        random.SystemRandom().choice(proof_filenames)
        if proof_filenames
        else None
    )
    solution_count = 2 if proof_filename else 3
    selected_hook = generate_and_select_hook(idea, app, content_style)

    content_prompt = f"""
Write the slide COPY for one TikTok/Reels image slideshow.

APP:
{app}

IDEA:
{idea}

STYLE:
{content_style}

PRESELECTED HOOK:
{json.dumps(selected_hook, ensure_ascii=False)}

The hook was selected from six candidates by a separate retention-scoring pass.
Copy its text and imageQuery exactly. Do not rewrite or replace it.

This is only the copywriting step. Python will put the slides in the correct
order and attach the images. Do not choose stage names or image-source types.

Write exactly:
- one 6-11 word hook that clearly states the situation and does not name the app
- one 7-14 word problem that clearly states the real consequence
- exactly {solution_count} solution steps of 7-14 words each; solution 1 must
  name {app['appName']} and plainly explain its core action
{f'- one 7-14 word proof caption that naturally states the benefit visible in the real image named {proof_filename!r}; never say "screenshot," "screen," "image," or "demonstrates"' if proof_filename else ''}
- one 7-14 word CTA naming {app['appName']} and giving one clear action

For the hook, problem, solutions, and CTA, include a concrete 2-6 word Pinterest
query. Queries describe visible people, objects, actions, or places. They must
not request UI, screenshots, text, logos, or abstract concepts.

COPY RULES:
- assume the viewer has never heard of the app
- never optimize for the fewest words; missing context is worse than length
- hook: 6-11 words; every other slide: 7-14 words
- use extremely simple words and one idea per slide
- be provocative, blunt, casual and emotionally sharp
- hook a specific mistake, fear, annoyance, cost or desired result
- make every solution say exactly what the person does
- name {app['appName']} in solution 1, not only at the end
- make the CTA name {app['appName']} and state exactly what it does
- every line must make sense without reading the generation prompt
- if a line could fit 100 unrelated apps, rewrite it
- use natural spoken sentences; cryptic fragments and slogan fragments are bad
- do not force drama with metaphors such as "betray," "lying," or "hiding"
- each slide must logically answer or advance the previous slide
- do not make unsupported claims
- no hashtags and no corporate language
- never use vague filler such as "peace of mind," "game changer," "take
  control," "when it matters," "stay organized," "made simple," "unlock,"
  "seamless," "you need this" or "next level"
- commit fully to the {content_style} style

TONE EXAMPLES (copy the directness, not the wording):
- BAD: "Crouch at pickup" / GOOD: "This rental angle catches scratches most people miss"
- BAD: "Your scan can betray you" / GOOD: "One missed ingredient can ruin every meal suggestion"
- BAD: "Check the list before recipes" / GOOD: "Check What2Cook's ingredient list before choosing your meal"
- BAD: "Screenshot shows editable ingredients" / GOOD: "Fix missing ingredients before What2Cook suggests your meals"

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
        elif (
            str(candidate["hook"]["text"]).strip() != selected_hook["text"].strip()
            or str(candidate["hook"]["imageQuery"]).strip()
            != selected_hook["imageQuery"].strip()
        ):
            last_content_error = "hook must exactly match the preselected hook"
        elif proof_filename and not str(candidate.get("proofText", "")).strip():
            last_content_error = "proofText is missing"
        elif (first_solution_text := str(solutions[0]["text"])) and app[
            "appName"
        ].casefold() not in first_solution_text.casefold():
            last_content_error = f"solution 1 must name {app['appName']}"
        elif (hook_error := _short_copy_error(
            candidate["hook"]["text"], "hook", 6, 11
        )):
            last_content_error = hook_error
        elif next(
            (
                error
                for label, text in [
                    ("problem", candidate["problem"]["text"]),
                    *(
                        (f"solution {index}", solution["text"])
                        for index, solution in enumerate(solutions, start=1)
                    ),
                    *([("proof", candidate["proofText"])] if proof_filename else []),
                    ("CTA", candidate["cta"]["text"]),
                ]
                if (error := _short_copy_error(text, label, 7, 14))
            ),
            None,
        ) is not None:
            last_content_error = next(
                error
                for label, text in [
                    ("problem", candidate["problem"]["text"]),
                    *(
                        (f"solution {index}", solution["text"])
                        for index, solution in enumerate(solutions, start=1)
                    ),
                    *([("proof", candidate["proofText"])] if proof_filename else []),
                    ("CTA", candidate["cta"]["text"]),
                ]
                if (error := _short_copy_error(text, label, 7, 14))
            )
        elif proof_filename and any(
            word in str(candidate["proofText"]).casefold()
            for word in ("screenshot", "screen", "image", "demonstrates")
        ):
            last_content_error = "proof caption must describe the benefit naturally"
        elif app["appName"].casefold() not in str(candidate["cta"]["text"]).casefold():
            last_content_error = f"CTA must name {app['appName']}"
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

Write one 12-28 word description that states exactly what the app does and why
someone would use it. Focus on one benefit instead of listing every feature.
Use easy everyday language, a direct CTA, and no corporate filler. Also write
3-5 relevant hashtags. Choose one real, existing song that fits the mood. Give
its exact title and artist.
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
        elif description_error := _short_copy_error(
            description, "description", 12, 28
        ):
            last_metadata_error = description_error
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
