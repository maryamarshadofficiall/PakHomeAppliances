from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Sample Reviews Data
raw_reviews = [
    {
        "product_name": "Haier 1.5 Ton Inverter AC (HSU-18HFP)",
        "score": 4.5,
        "pros": ["45 degree garmi mein zabardast cooling", "Low voltage par chal jata hai"],
        "cons": ["Outdoor unit thoda loud hai", "Installation charges extra hain"],
        "verdict": "Kam voltage wale areas ke liye behtareen aur durable choice hai."
    },
    {
        "product_name": "Dawlance 1.5 Ton Chrome Inverter AC",
        "score": 4.2,
        "pros": ["Bohot stylish aur modern design", "Electricity bill kafi kam aata hai"],
        "cons": ["Room cool hone mein 20 mins lagte hain", "Filter maintenance required"],
        "verdict": "Bijli ki bachat aur stylish look ke liye achi choice hai."
    }
]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "products": raw_reviews})