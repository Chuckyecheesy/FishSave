"""
Quick test that Gemini API key in .env works (one generate_content call).
Run: python test_gemini_key.py
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None

load_dotenv(Path(__file__).parent / ".env")
key = os.environ.get("GEMINI_API_KEY")
if not key:
    print("No GEMINI_API_KEY in .env")
    exit(1)
print("Key loaded (first 8 chars):", key[:8] + "...")

try:
    import google.generativeai as genai
    genai.configure(api_key=key)
    for name in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"):
        try:
            model = genai.GenerativeModel(name)
            r = model.generate_content("Say OK in one word.")
            if r and r.text:
                print("Model:", name)
                print("Gemini response:", r.text.strip())
                print("SUCCESS: Gemini key works.")
                break
        except Exception as e:
            print("Model", name, "->", e)
    else:
        print("All models failed.")
except Exception as e:
    print("Gemini error:", e)
