"""SiliconFlow (硅基流动) 适配器 —— OpenAI 兼容 API"""

from .base import BaseAdapter


class SiliconFlowAdapter(BaseAdapter):
    name = "siliconflow"
    base_url = "https://api.siliconflow.cn/v1"
    api_key_env = "SILICONFLOW_API_KEY"

    def preprocess_chat_request(self, chat_req: dict) -> dict:
        super().preprocess_chat_request(chat_req)

        stop = chat_req.get("stop")
        if isinstance(stop, list) and len(stop) > 4:
            chat_req["stop"] = stop[:4]

        # SiliconFlow 上的 DeepSeek 模型需要禁用 thinking 避免推理循环
        model = chat_req.get("model", "")
        if "deepseek" in model.lower():
            if "thinking" not in chat_req:
                chat_req["thinking"] = {"type": "disabled"}

        return chat_req
