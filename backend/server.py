from dotenv import load_dotenv  # reads your .env file
load_dotenv()  # loads the keys before anything else runs

import logging  # so unexpected errors still get recorded in the terminal
import os  # lets us check the keys exist
from typing import Optional  # marks the upload as "may be missing"
from fastapi import FastAPI, UploadFile, File, HTTPException, Request  # the server + photo-upload tools
from fastapi.concurrency import run_in_threadpool  # runs the slow API calls without freezing the server
from fastapi.middleware.cors import CORSMiddleware  # lets your frontend talk to this server
from fastapi.responses import JSONResponse  # for our catch-all error reply
from cal import identify_food, FoodIdError  # step 1: photo -> food phrase
from nutrition import lookup_nutrition, sum_nutrition, slim_item, NutritionError  # step 2: phrase -> numbers

REQUIRED_KEYS = ["ANTHROPIC_API_KEY", "CALORIENINJAS_KEY"]  # both must be in .env
log = logging.getLogger("calai")  # our logger

app = FastAPI()  # create the server

app.add_middleware(  # add a rule to the server
    CORSMiddleware,  # the "who can call us" rule
    allow_origins=["*"],  # allow any frontend for now
    allow_methods=["*"],  # allow any request type
    allow_headers=["*"],  # allow any headers
)

@app.exception_handler(Exception)  # last line of defence: never send a raw crash
async def unexpected_error(request: Request, exc: Exception):
    log.exception("Unexpected error on %s", request.url.path)  # full traceback goes to the terminal
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})  # client gets a clean message

@app.get("/health")  # quick "is the server up?" check
def health():
    return {"status": "ok"}

@app.post("/analyze")  # when a photo is POSTed to "/analyze", run this
async def analyze(file: Optional[UploadFile] = File(None)):  # receive the uploaded photo (None if missing)
    if file is None:  # no "file" field in the form
        raise HTTPException(400, "No image uploaded. Send it as form field 'file'.")
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]  # check keys before spending any API calls
    if missing:
        raise HTTPException(500, f"Server misconfigured: missing {', '.join(missing)} in .env.")

    contents = await file.read()  # read the raw bytes
    try:
        food_phrase = await run_in_threadpool(identify_food, contents)  # step 1: Claude names the food
        items = await run_in_threadpool(lookup_nutrition, food_phrase)  # step 2: database looks up the numbers
    except (FoodIdError, NutritionError) as e:  # any known failure -> its HTTP code + message
        raise HTTPException(e.status_code, str(e))

    return {
        "food_phrase": food_phrase,  # what Claude saw, e.g. "200g grilled chicken, 1 cup rice"
        "items": [slim_item(i) for i in items],  # per-food breakdown
        "totals": sum_nutrition(items),  # everything added up
    }
