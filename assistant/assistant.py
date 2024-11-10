import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


def use_assistant(prompt):
    """Generate text based on the given prompt."""

    PRE_PROMPT = """
        You are an AI assistant that can help me with my tasks and answering questions during a meeting.
        Your name is Flux and your wake command is "Okay Flux".
        Your text is going to go to a text to speech service to be converted to speech.
        Do not include emojis or special characters in your responses.
        You should respond concisely and clearly, just like Siri would. Provide helpful and accurate information.
    """

    try: 
        prompt = f"{PRE_PROMPT}\nPrompt: {prompt}"

        response = model.generate_content(prompt)
    except Exception as e:
        response = str(e)
    return response.candidates[0].content.parts[0].text

def get_summary(text):
    """Generate a summary of the given text."""

    PRE_PROMPT = """
        Summarize the following text.
    """

    prompt = f"{PRE_PROMPT}\n{text}"

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        response = str(e)
    return response.candidates[0].content.parts[0].text

def get_tagline(text):
    """Generate a tagline of the given text."""

    PRE_PROMPT = """
        Generate a short summary of the given text. (1 to 2 sentences) 
        Only give me one option. Don't include special characters, emojis, or anything that would be hard to convert to speech.

    """

    prompt = f"{PRE_PROMPT}\n{text}"

    try:
        response = model.generate_content(prompt)
        print(response)
    except Exception as e:
        response = str(e)
    return response.candidates[0].content.parts[0].text

def get_tags(text, tags):
    """See if the given text contains the specified tags."""
    
    PRE_PROMPT = """
        Determine if the following text contains the specified tags.

        Return in a Json format.
    """

    prompt = f"{PRE_PROMPT}\n{text}\nTags: {tags}"

    try:
        response = model.generate_content(prompt)
        print(response)
    except Exception as e:
        response = str(e)
    return response.candidates[0].content.parts[0].text.replace('```json\n', '').replace('```', '')

def get_kanban(text):
    """Generate a kanban board based on the given text."""

    PRE_PROMPT = """
        Generate a kanban board based on the following text.

        It should have four columns: To Do, In Progress, Done, and Blocked.

        Each task should contain a title, description, status, assigned, tag, due date, is it a bug or feature and priority (low, medium, or high).

        Return in a Json format. Only give me the JSON. Only add items if they are actual tasks, do not add placeholders.
    """

    prompt = f"{PRE_PROMPT}\n{text}"

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        response = str(e)
    return response.candidates[0].content.parts[0].text.replace('```json\n', '').replace('```', '')