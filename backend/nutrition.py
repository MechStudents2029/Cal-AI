from dotenv import load_dotenv  # reads your .env file
load_dotenv()  # loads the key before anything else runs

import os  # lets us read the key from the environment
import requests  # makes the HTTP call to CalorieNinjas

class NutritionError(Exception):  # one error type for everything that can go wrong in this step
    def __init__(self, message, status_code):  # carry an HTTP code along with the message
        super().__init__(message)  # the human-readable reason
        self.status_code = status_code  # what the server should send back

def lookup_nutrition(food_phrase):          # the "nutritionist": phrase in, facts out
    api_key = os.getenv("CALORIENINJAS_KEY")             # grab your key
    if not api_key:                                      # no key = every call gets rejected
        raise NutritionError("Server misconfigured: CALORIENINJAS_KEY is not set.", 500)
    url = "https://api.calorieninjas.com/v1/nutrition"   # the endpoint
    headers = {"X-Api-Key": api_key}                     # prove who we are with the key
    params = {"query": food_phrase}                      # the phrase, safely encoded
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)  # ask the nutrition database
    except requests.RequestException:                    # timeout, DNS failure, no internet...
        raise NutritionError("Could not reach the CalorieNinjas API.", 503)

    if r.status_code in (401, 403):                      # key is wrong or expired
        raise NutritionError("Server misconfigured: CALORIENINJAS_KEY was rejected.", 500)
    if r.status_code != 200:                             # any other failure on their side
        raise NutritionError(f"CalorieNinjas API error ({r.status_code}).", 502)
    try:
        data = r.json()                                  # turn the reply into a dictionary
    except ValueError:                                   # reply wasn't JSON at all
        raise NutritionError("CalorieNinjas returned a non-JSON response.", 502)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):  # missing "items"
        raise NutritionError("CalorieNinjas response did not contain 'items'.", 502)
    if not data["items"]:                                # valid reply, but nothing matched
        raise NutritionError(f"No nutrition data found for: {food_phrase}", 422)
    return data["items"]                                 # list of foods with their nutrition

def slim_item(item):                        # keep just the fields we care about from one item
    return {
        "name": item.get("name"),                                    # e.g. "grilled chicken"
        "serving_size_g": round(item.get("serving_size_g") or 0, 1),  # how much was looked up
        "calories": round(item.get("calories") or 0, 1),             # kcal
        "protein_g": round(item.get("protein_g") or 0, 1),           # protein
        "carbs_g": round(item.get("carbohydrates_total_g") or 0, 1), # CalorieNinjas' name for carbs
        "fat_g": round(item.get("fat_total_g") or 0, 1),             # CalorieNinjas' name for fat
    }

def sum_nutrition(items):                   # add up every item into one set of totals
    totals = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}  # start at zero
    for item in items:                                   # go through each food
        slim = slim_item(item)                           # normalise the field names
        for key in totals:                               # add each nutrient
            totals[key] += slim[key]
    return {key: round(value, 1) for key, value in totals.items()}  # tidy up the decimals
