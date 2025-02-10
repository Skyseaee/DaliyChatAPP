import uuid
import chromadb
from chromadb.utils import embedding_functions
from flask import Flask
import requests
from langchain_openai import ChatOpenAI
from langchain.chains import RunnableSequence

from langchain.chains import LLMChain  # 修改为使用LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from textblob import TextBlob
from app import app

# 初始化 ChromaDB 客户端
chroma_client = chromadb.Client()
OPENAI_API_KEY = app.config['OPENAI_API_KEY']

# 尝试从 Flask 应用中获取 SECRET_KEY，如果没有则使用默认值
try:
    SECRET_KEY = app.config['SECRET_KEY']
except Exception:
    SECRET_KEY = "default_secret_key"

# 初始化 OpenAI embedding 函数
# openai_ef = embedding_functions.OpenAIEmbeddingFunction(
#     api_key=OPENAI_API_KEY,
#     model_name="text-embedding-ada-002"
# )

# 初始化 Huggingface embedding 函数
class HuggingFaceEmbedding:
    def __init__(self):
        self.API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
        self.headers = {"Authorization": f"Bearer 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"}

    def __call__(self, input):
        payload = {
            "inputs": input,
            "options": {"wait_for_model": True}
        }
        response = requests.post(self.API_URL, headers=self.headers, json=payload)
        return response.json()

# 获取或创建用户的集合
def get_user_collection(user_id):
    collection_name = f"user_{user_id}_diary_conversations"
    embedding_function = HuggingFaceEmbedding()
    return chroma_client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)

# 分析文本情感
def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

# 增强积极情绪（如果情感分析结果为负，则在前面添加积极提示）
def enhance_positive_sentiment(text):
    if analyze_sentiment(text) < 0:
        return f"虽然今天有些挑战，但我相信一切都会好起来的。{text}"
    return text

def get_latest_conversation_summary(user_id):
    collection = get_user_collection(user_id)
    results = collection.query(
        where={"source": "user_conversation"},
        n_results=10  # 获取更多结果以便排序
    )
    if results.get('documents'):
        # 按照 'timestamp' 排序
        sorted_docs = sorted(results['documents'], key=lambda x: x.get('timestamp', 0), reverse=True)
        return sorted_docs[0]
    return ""


def summarize_conversation(user_id, conversation):
    # 初始化自定义LLM
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        openai_api_base="https://api.deepseek.com/v1",  # 自定义API端点
        model_name="deepseek-chat",  # 根据实际模型名称调整
        temperature=0.3,           # 控制生成随机性（0-1）
        max_tokens=512,            # 控制生成长度
        streaming=False,           # 是否启用流式传输
    )

    # 创建Prompt
    prompt_template = PromptTemplate(
        input_variables=["latest_summary", "conversation"],
        template="""
        <系统指令>
        你是一个专业的日记优化助手，请按照以下要求处理对话：
        1. 保持原意的前提下简化内容
        2. 使用积极乐观的表达方式
        3. 适当补充合理的细节
        4. 输出长度控制在200字以内
        
        <历史记录>
        {latest_summary}
        
        <当前对话>
        {conversation}
        
        <优化结果>
        """
    )

    # 构建处理链，使用 RunnableSequence 替代 LLMChain
    chain = prompt_template | llm  # 使用管道操作符（|）来连接 prompt_template 和 llm

    try:
        # 获取最新对话摘要
        latest_summary = get_latest_conversation_summary(user_id)
        
        # 调用链处理对话
        response = chain.invoke({
            "latest_summary": latest_summary,
            "conversation": conversation
        })
        
        # 处理响应格式（不同版本可能返回不同结构）
        summary_text = response.get("text", response.get("result", str(response)))
        
        # 增强积极情感
        return enhance_positive_sentiment(summary_text.strip())
    
    except Exception as e:
        # 捕获异常并返回原始对话内容
        print(f"对话摘要生成失败: {str(e)}")
        return enhance_positive_sentiment(conversation)  # 降级处理
# 向集合中添加对话记录
def add_conversation(user_id, conversation):
    collection = get_user_collection(user_id)
    # 对对话进行总结
    summarized_conversation = summarize_conversation(user_id, conversation)
    collection.add(
        documents=[summarized_conversation],
        metadatas=[{"source": "user_conversation"}],
        ids=[str(uuid.uuid4())]  # 使用 uuid 生成唯一 id
    )

# 获取用户所有对话记录（这里假设能获取到当天所有对话）
def get_all_conversations(user_id):
    collection = get_user_collection(user_id)
    results = collection.query(
        where={"source": "user_conversation"},
        n_results=1000
    )
    return " ".join(results.get('documents', []))

# 仅作为测试 huggingface_embedding 函数用
if __name__ == '__main__':
    text = "这是一个测试文本"
    embedding = huggingface_embedding(text)
    print(embedding)
