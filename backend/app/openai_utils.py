import openai
from app import app

OPENAI_API_KEY = app.config['OPENAI_API_KEY']

# Define templates for different personalities
TEMPLATES = {
    "友好风格": """
    你是一位亲切友好且乐于助人的助手。请以亲切自然、礼貌的对话方式回应以下用户的输入：

    User: {user_input}

    Assistant: 您好呀，我来为您好好解答啦。
    """,
    "正式风格": """
    你是一位正式且专业的助手。请以恭敬、严谨、准确的态度回应以下用户的输入：

    用户：{user_input}

    助手：尊敬的用户，针对您提出的问题，以下是详细且专业的回复。
    """,
    "幽默风格": """
    你是一位幽默风趣、机智俏皮的助手。请带着轻松愉快的幽默感回应以下用户的输入：

    用户：{user_input}

    助手：嘿呀，听您这话呀，就像给我出了个超有趣的小谜题呢，且看我逗趣地给您解一解！
    """,
    "共情风格": """
    你是一位善解人意、富有同理心的助手。请带着理解和支持回应以下用户的输入：

    用户：{user_input}

    助手：我完全能体会到您此刻的感受，别着急，咱们一起想办法来解决。
    """
}

def generate_summary_stream(prompt, personality: str = "友好风格"):
    """处理流式响应的函数"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.deepseek.com")
    template = TEMPLATES.get(personality, TEMPLATES["友好风格"])
    formatted_prompt = template.format(user_input=prompt)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": formatted_prompt}
        ],
        stream=True,  # 启用流式响应
    )

    result = ""
    for part in response:
        if hasattr(part, 'choices') and len(part.choices) > 0:
            choice = part.choices[0]
            if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                result += choice.delta.content
                yield result  # 使用生成器返回中间状态

def generate_summary(prompt, personality: str = "友好风格"):
    """处理非流式响应的函数"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.deepseek.com")
    template = TEMPLATES.get(personality, TEMPLATES["友好风格"])
    formatted_prompt = template.format(user_input=prompt)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": formatted_prompt}
        ],
        stream=False,  # 禁用流式响应
    )

    return response

def seek_chat_service(prompt, stream: bool=False):
    openai.api_key = OPENAI_API_KEY 

    client = openai.OpenAI(api_key=openai.api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt}
        ],
        stream=stream,
    )
    return response

# Example usage
if __name__ == "__main__":
    prompt = "你好，今天天气怎么样？"
    response = generate_summary(prompt, personality="友好风格")
    print(response.choices[0].message.content)