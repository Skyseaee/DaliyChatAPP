from vector_db import huggingface_embedding 

if __name__ == '__main__':
    text = "这是一个测试文本"
    embedding = huggingface_embedding(text)
    print(embedding)