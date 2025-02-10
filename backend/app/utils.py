import onnxruntime as ort
import numpy as np
from sentence_transformers import SentenceTransformer
import torch


class ONNXEmbeddingService:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        # 加载并转换模型为 ONNX 格式
        self.model = SentenceTransformer(model_name)
        input_names = ['input_ids', 'attention_mask']
        output_names = ['sentence_embedding']
        dummy_input = {
            'input_ids': torch.randint(0, 1000, (1, 128)),
            'attention_mask': torch.ones((1, 128), dtype=torch.long)
        }
        torch.onnx.export(
            self.model,
            (dummy_input['input_ids'], dummy_input['attention_mask']),
            f"{model_name}.onnx",
            input_names=input_names,
            output_names=output_names,
            dynamic_axes={
                'input_ids': {0: 'batch_size', 1: 'sequence_length'},
                'attention_mask': {0: 'batch_size', 1: 'sequence_length'}
            }
        )
        # 加载 ONNX 模型
        self.ort_session = ort.InferenceSession(f"{model_name}.onnx")

    def get_embedding(self, text):
        # 对输入文本进行分词
        inputs = self.model.tokenize(text)
        input_ids = inputs['input_ids'].unsqueeze(0).numpy()
        attention_mask = inputs['attention_mask'].unsqueeze(0).numpy()
        # 运行推理
        outputs = self.ort_session.run(
            None,
            {'input_ids': input_ids, 'attention_mask': attention_mask}
        )
        embedding = outputs[0][0]
        return embedding


# 服务初始化时加载模型
embedding_service = ONNXEmbeddingService()


def generate_embedding(text):
    return embedding_service.get_embedding(text)


# 示例调用
if __name__ == '__main__':
    text = "这是一个测试文本"
    embedding = generate_embedding(text)
    print(embedding)