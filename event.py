import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller creates a temp folder and stores path in _MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

import nltk
import re
import requests
import webbrowser
from threading import Timer
from flask import Flask, render_template, request
from bs4 import BeautifulSoup


nltk.download('stopwords')
from nltk.corpus import stopwords


STOPWORDS_FILE = resource_path("stopwords.txt")

if not os.path.exists(STOPWORDS_FILE):
    print("Downloading stopwords...")
    stop_words_set = set(stopwords.words("english"))
    with open("stopwords.txt", "w") as f:
        f.write("\n".join(stop_words_set))
    print("Stopwords saved to stopwords.txt.")
else:
    print("Stopwords file already exists.")

with open(STOPWORDS_FILE, "r") as f:
    stop_words = set(f.read().splitlines())


app = Flask(__name__, template_folder=resource_path("templates"))

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5002/")

def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9°%\'\- ]", "", text)
    text = text.lower()
    text = " ".join([word for word in text.split() if word not in stop_words])
    return text

def classify_headline(text):
    political_keywords = [
        "war", "election", "government", "russia", "ukraine", "biden", "trump", "modi", 
        "parliament", "congress", "minister", "law", "policy", "bill", "senate", "diplomacy"
    ]
    sports_keywords = [
        "cricket", "football", "tennis", "fifa", "olympics", "nba", "nfl", "match", "tournament",
        "goal", "medal", "score", "team", "player", "world cup", "grand slam", "league", "champion",
        "race", "formula", "verstappen", "run", "bat", "wicket", "stadium"
    ]
    economy_keywords = [
        "economy", "trade", "tariff", "business", "finance", "stock market", "inflation", "GDP",
        "investment", "shares", "rupee", "dollar", "budget"
    ]
    weather_keywords = [
        "storm", "hurricane", "earthquake", "rain", "snow", "flood", "temperature", "humidity",
        "heatwave", "wildfire", "cyclone", "cold snap", "drought", "climate", "tornado"
    ]

    cleaned_text_str = clean_text(text)

    if any(word in cleaned_text_str for word in political_keywords):
        return "Political News"
    elif any(word in cleaned_text_str for word in sports_keywords):
        return "Sports"
    elif any(word in cleaned_text_str for word in economy_keywords):
        return "Economy & Trade"
    elif any(word in cleaned_text_str for word in weather_keywords):
        return "Weather"
    else:
        return "General News"

def extract_weather_details(text):
    temperature_match = re.search(r"(-?\d+°C)", text)
    humidity_match = re.search(r"(\d+% humidity)", text)

    temperature = temperature_match.group(1) if temperature_match else None
    humidity = humidity_match.group(1) if humidity_match else None

    weather_info = []
    if temperature:
        weather_info.append(f"Temp: {temperature}")
    if humidity:
        weather_info.append(f"Humidity: {humidity}")

    return " | ".join(weather_info) if weather_info else None

def extract_news_headlines(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        headlines = soup.find_all(["h1", "h2", "h3"])

        extracted_headlines = {
            "Political News": set(),
            "Sports": set(),
            "Economy & Trade": set(),
            "Weather": set(),
            "General News": set(),
        }
        
        unwanted_sections = [
            "Trending", "Most Read", "Must Read", "Most Watched", "Most Popular", "Watch", "Opinion", "Something Extra", "More of the latest stories", "Video",
            "Featured", "More Headlines", "Al Jazeera", "Follow BBC on", "More to explore", "You may have missed", "Around the world", "World in photos",
            "Also in news", "Videos", "In pictures", "News in focus", "Deeply read", "Headlines", "Most viewed", "Spotlight", "Take part", "Sport", "Business", "Entertainment", "Content Feed", "Politics", "NewsNews"
        ]

        for headline in headlines:
            text = headline.get_text(strip=True)

            if any(phrase.lower() in text.lower() for phrase in unwanted_sections) or len(text) < 5:
                continue

            category = classify_headline(text)

            if category == "Weather":
                weather_info = extract_weather_details(text)
                formatted_text = f"{text} ({weather_info})" if weather_info else text
                extracted_headlines[category].add(formatted_text)
            else:
                extracted_headlines[category].add(text)

        return extracted_headlines

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.route("/", methods=["GET", "POST"])
def index():
    headlines = None
    url = ""

    if request.method == "POST":
        url = request.form.get("url")
        headlines = extract_news_headlines(url)

    return render_template("index.html", headlines=headlines, url=url)

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(port=5002, debug=False)
