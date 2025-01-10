import chromadb
from chromadb.utils import embedding_functions
import openai
from chatAI.backend.config import Config
from langchain.chains import SimpleChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from textblob import TextBlob

# Initialize ChromaDB client
chroma_client = chromadb.Client()

# Initialize OpenAI embedding function
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=Config.OPENAI_API_KEY,
    model_name="text-embedding-ada-002"
)

# Function to get or create a user collection
def get_user_collection(user_id):
    collection_name = f"user_{user_id}_diary_conversations"
    return chroma_client.get_or_create_collection(name=collection_name, embedding_function=openai_ef)

# Function to analyze sentiment
def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

# Function to enhance positive sentiment
def enhance_positive_sentiment(text):
    if analyze_sentiment(text) < 0:
        return f"虽然今天有些挑战，但我相信一切都会好起来的。{text}"
    return text

# Function to get the latest conversation summary
def get_latest_conversation_summary(user_id):
    collection = get_user_collection(user_id)
    results = collection.query(
        where={"source": "user_conversation"},
        n_results=1,
        sort_by="timestamp",
        sort_order="desc"
    )
    if results['documents']:
        return results['documents'][0]
    return ""

# Function to summarize the conversation using LangChain
def summarize_conversation(user_id, conversation):
    openai.api_key = Config.OPENAI_API
    llm = OpenAI(api_key=Config.OPENAI_API_KEY, model="text-davinci-003")
    latest_summary = get_latest_conversation_summary(user_id)
    prompt_template = PromptTemplate(
        input_variables=["latest_summary", "conversation"],
        template=(
            "请对以下对话进行简化，并使其内容更加丰富和积极乐观：\n\n"
            "之前的日记内容：\n{latest_summary}\n\n"
            "当前对话内容：\n{conversation}\n\n"
            "简化后的对话："
        )
    )
    chain = SimpleChain(llm=llm, prompt_template=prompt_template)
    summary = chain.run({"latest_summary": latest_summary, "conversation": conversation})
    return enhance_positive_sentiment(summary.strip())

# Function to add a conversation to the collection
def add_conversation(user_id, conversation):
    collection = get_user_collection(user_id)
    
    # Summarize the conversation
    summarized_conversation = summarize_conversation(user_id, conversation)
    
    collection.add(
        documents=[summarized_conversation],
        metadatas=[{"source": "user_conversation"}],
        ids=[str(len(collection))]
    )

# Function to get all conversations for a user
def get_all_conversations(user_id):
    collection = get_user_collection(user_id)
    results = collection.query(
        where={"source": "user_conversation"},
        n_results=1000  # 假设这里能获取到当天所有对话
    )
    return " ".join(results['documents'])