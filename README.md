# Cal AI clone (backend)

Send a photo of a meal and get back calories, protein, carbs and fat.

It works in two steps:

1. **Claude** (`claude-sonnet-4-6`) looks at the photo and writes a plain food phrase with amounts, such as `200g grilled chicken, 1 cup white rice`. Claude never produces the calorie numbers.
2. **CalorieNinjas** looks that phrase up in its nutrition database. The server then adds the items together.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in this folder:

```
ANTHROPIC_API_KEY=sk-ant-...
CALORIENINJAS_KEY=your-calorieninjas-key
```

- Anthropic key: https://console.anthropic.com
- CalorieNinjas key: https://calorieninjas.com/api

`.env` is listed in `.gitignore`, so it is never committed.

## Run

```bash
uvicorn server:app --reload
```

The server runs at http://127.0.0.1:8000. Interactive docs are at http://127.0.0.1:8000/docs.

## Test

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}

curl -X POST -F "file=@meal.jpg" http://127.0.0.1:8000/analyze
```

Example response (the numbers are made up to show the format):

```json
{
  "food_phrase": "200g grilled chicken, 1 cup white rice",
  "items": [
    {"name": "grilled chicken", "serving_size_g": 200.0, "calories": 380.2, "protein_g": 47.6, "carbs_g": 0.0, "fat_g": 19.8},
    {"name": "white rice", "serving_size_g": 158.0, "calories": 202.5, "protein_g": 4.2, "carbs_g": 44.4, "fat_g": 0.4}
  ],
  "totals": {"calories": 582.7, "protein_g": 51.8, "carbs_g": 44.4, "fat_g": 20.2}
}
```

## Errors

Every error comes back as `{"detail": "..."}` with one of these status codes:

| Code | Meaning |
|------|---------|
| 400 | No image uploaded, empty file, or Claude couldn't read the image |
| 413 | Image is larger than 5 MB |
| 415 | Not a JPEG, PNG, GIF or WEBP |
| 422 | No food detected, or CalorieNinjas found no match |
| 500 | API key missing or rejected (check `.env`) |
| 502 | An upstream API returned a bad or empty response, or a reply with no `items` |
| 503 | An upstream API is unreachable or rate-limiting |

You can also check step 1 on its own: `python cal.py meal.jpg` prints the food phrase.
