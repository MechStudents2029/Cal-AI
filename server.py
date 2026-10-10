from dotenv import load_dotenv  # reads your .env file
load_dotenv()  # loads the key before anything else runs

from fastapi import FastAPI, UploadFile, File  # the server + photo-upload tools
from fastapi.middleware.cors import CORSMiddleware  # lets your frontend talk to this server
from cal import analyze_meal  # borrow the brain from cal.py — no duplicated code

app = FastAPI()  # create the server

app.add_middleware(  # add a rule to the server
    CORSMiddleware,  # the "who can call us" rule
    allow_origins=["*"],  # allow any frontend for now
    allow_methods=["*"],  # allow any request type
    allow_headers=["*"],  # allow any headers
)

@app.post("/analyze")  # when a photo is POSTed to "/analyze", run this
async def analyze(file: UploadFile = File(...)):  # receive the uploaded photo
    contents = await file.read()  # read the raw bytes
    return analyze_meal(contents, file.content_type)  # hand bytes + real type to the brain