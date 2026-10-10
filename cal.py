from dotenv import load_dotenv  # the tool that reads your .env file
load_dotenv()  # loads your API key from .env before anything else runs

import anthropic  # the toolkit that talks to Claude
import base64  # packages the image as text so it can be sent in the request
import json  # turns the reply text into a Python dictionary
import sys  # lets us read the photo's name from the command line

client = anthropic.Anthropic()  # opens the connection; it finds your API key automatically

def analyze_meal(image_bytes, media_type="image/jpeg"):  # takes raw image bytes + the file's real type
    image_data = base64.b64encode(image_bytes).decode("utf-8")  # encode the bytes to text

    prompt = (  # the instructions we hand the model
        "Look at this meal. Reply with ONLY JSON like: "  # demand JSON, nothing else
        '{"food": str, "calories": int, "protein_g": int, '  # fields: name, calories, protein
        '"carbs_g": int, "fat_g": int}. '  # fields: carbs, fat
        "Estimate for the portion shown."  # guess for the portion in the picture
    )

    response = client.messages.create(  # send everything to Claude
        model="claude-sonnet-4-6",  # the model doing the looking
        max_tokens=300,  # cap how long the reply can be
        messages=[{  # one message from us, the user
            "role": "user",  # marks this as our turn
            "content": [  # the message has two pieces:
                {"type": "image", "source": {  # piece 1: the photo
                    "type": "base64",  # sent as encoded text
                    "media_type": media_type,  # use whatever type the file actually is
                    "data": image_data}},  # the encoded photo itself
                {"type": "text", "text": prompt},  # piece 2: our instructions
            ],
        }],
    )

    text = response.content[0].text  # pull the plain text out of the reply
    text = text.replace("```json", "").replace("```", "").strip()  # strip code fences if any
    return json.loads(text)  # turn the JSON text into a real dictionary

if __name__ == "__main__":  # only runs when we launch cal.py directly
    with open(sys.argv[1], "rb") as f:  # open the photo we typed, as bytes
        result = analyze_meal(f.read())  # hand those bytes to the brain
    print(result)  # print the nutrition back to us