import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

PRE_PROMPT = """
You are an AI assistant that can help me with my tasks and answering questions during a meeting.
"""

def generate_text(prompt):
    """Generate text based on the given prompt."""
    try: 
        prompt = f"{PRE_PROMPT}\nPrompt: {prompt}"

        response = model.generate_content(prompt)
    except Exception as e:
        response = str(e)
    return response