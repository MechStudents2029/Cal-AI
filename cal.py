from dotenv import load_dotenv  # the tool that reads your .env file
load_dotenv()  # loads your API key from .env before anything else runs

import anthropic  # the toolkit that talks to Claude
import base64  # packages the image as text so it can be sent in the request
import os  # lets us check that the API key actually exists
import sys  # lets us read the photo's name from the command line

MODEL = "claude-sonnet-4-6"  # the model doing the looking
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # Claude rejects images over 5 MB, so we stop them early
NO_FOOD = "NO_FOOD"  # the exact word Claude replies with when there's no food in the photo

class FoodIdError(Exception):  # one error type for everything that can go wrong in this step
    def __init__(self, message, status_code):  # carry an HTTP code along with the message
        super().__init__(message)  # the human-readable reason
        self.status_code = status_code  # what the server should send back (400, 502, ...)

def detect_media_type(image_bytes):  # figure out the real image type from the file's first bytes
    if image_bytes.startswith(b"\xff\xd8\xff"):  # JPEG signature
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG signature
        return "image/png"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):  # GIF signature
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":  # WEBP signature
        return "image/webp"
    return None  # not an image Claude can read

def identify_food(image_bytes):  # photo bytes in, plain food phrase out (no numbers from Claude)
    if not image_bytes:  # empty upload
        raise FoodIdError("The uploaded image is empty.", 400)
    if len(image_bytes) > MAX_IMAGE_BYTES:  # too big for the API
        raise FoodIdError("Image is larger than 5 MB.", 413)
    media_type = detect_media_type(image_bytes)  # trust the bytes, not the filename
    if media_type is None:  # e.g. a PDF or a renamed text file
        raise FoodIdError("Unsupported or corrupt image. Use JPEG, PNG, GIF or WEBP.", 415)
    if not os.getenv("ANTHROPIC_API_KEY"):  # no key = nothing will work
        raise FoodIdError("Server misconfigured: ANTHROPIC_API_KEY is not set.", 500)

    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")  # encode the bytes to text

    prompt = (  # the instructions we hand the model
        "Identify every food and drink in this photo and estimate the portion shown. "
        "Reply with ONLY a single line: a comma-separated list of items, each as "
        "amount + unit + simple food name, e.g. '200g grilled chicken, 1 cup white rice, 1 tbsp olive oil'. "
        "Prefer grams for solid foods. Do NOT include calories, macros, explanations or any other text. "
        f"If there is no food in the photo, reply with exactly {NO_FOOD}."
    )

    client = anthropic.Anthropic()  # opens the connection; it finds your API key automatically
    try:
        response = client.messages.create(  # send everything to Claude
            model=MODEL,  # the model doing the looking
            max_tokens=300,  # a food list is short; cap the reply
            messages=[{  # one message from us, the user
                "role": "user",  # marks this as our turn
                "content": [  # the message has two pieces:
                    {"type": "image", "source": {  # piece 1: the photo
                        "type": "base64",  # sent as encoded text
                        "media_type": media_type,  # the type we detected from the bytes
                        "data": image_data}},  # the encoded photo itself
                    {"type": "text", "text": prompt},  # piece 2: our instructions
                ],
            }],
        )
    except anthropic.AuthenticationError:  # key exists but is wrong
        raise FoodIdError("Server misconfigured: ANTHROPIC_API_KEY was rejected.", 500)
    except anthropic.BadRequestError as e:  # usually an image Claude can't decode
        raise FoodIdError(f"Claude could not process this image: {e.message}", 400)
    except anthropic.RateLimitError:  # too many requests
        raise FoodIdError("Claude is rate-limiting us. Try again shortly.", 503)
    except anthropic.APIConnectionError:  # network problem or timeout
        raise FoodIdError("Could not reach the Claude API.", 503)
    except anthropic.APIStatusError as e:  # any other API-side failure
        raise FoodIdError(f"Claude API error ({e.status_code}).", 502)

    if response.stop_reason == "refusal":  # Claude declined to look at it
        raise FoodIdError("Claude declined to analyze this image.", 422)

    text = "".join(b.text for b in response.content if b.type == "text")  # pull out the plain text
    phrase = text.strip().strip("`").strip()  # drop whitespace and stray code fences
    if not phrase:  # Claude sent back nothing usable
        raise FoodIdError("Claude returned an empty response.", 502)
    if phrase.upper().startswith(NO_FOOD):  # nothing edible in the photo
        raise FoodIdError("No food detected in the image.", 422)
    return phrase  # e.g. "200g grilled chicken, 1 cup white rice"

if __name__ == "__main__":  # only runs when we launch cal.py directly
    with open(sys.argv[1], "rb") as f:  # open the photo we typed, as bytes
        print(identify_food(f.read()))  # print the food phrase Claude saw
