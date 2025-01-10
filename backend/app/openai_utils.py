import openai
from chatAI.backend.config import Config

# Define templates for different personalities
TEMPLATES = {
    "friendly": """
    You are a friendly and helpful assistant. Please respond to the following user input in a conversational and polite manner:

    User: {user_input}

    Assistant:
    """,
    "formal": """
    You are a formal and professional assistant. Please respond to the following user input in a respectful and precise manner:

    User: {user_input}

    Assistant:
    """,
    "humorous": """
    You are a humorous and witty assistant. Please respond to the following user input with a touch of humor and light-heartedness:

    User: {user_input}

    Assistant:
    """,
    "empathetic": """
    You are an empathetic and understanding assistant. Please respond to the following user input with empathy and support:

    User: {user_input}

    Assistant:
    """
}

def generate_summary(prompt, personality="friendly"):
    openai.api_key = Config.OPENAI_API_KEY
    
    # Select the appropriate template based on the personality type
    template = TEMPLATES.get(personality, TEMPLATES["friendly"])
    
    # Format the prompt using the selected template
    formatted_prompt = template.format(user_input=prompt)
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": formatted_prompt}
        ]
    )
    return response