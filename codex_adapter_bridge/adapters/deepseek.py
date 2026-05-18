"""DeepSeek 适配器"""

from .base import BaseAdapter


class DeepSeekAdapter(BaseAdapter):
    name = "deepseek"
    base_url = "https://api.deepseek.com/v1"
    api_key_env = "DEEPSEEK_API_KEY"

    def preprocess_chat_request(self, chat_req: dict) -> dict:
        super().preprocess_chat_request(chat_req)

        stop = chat_req.get("stop")
        if isinstance(stop, list) and len(stop) > 4:
            chat_req["stop"] = stop[:4]

        if "thinking" not in chat_req:
            chat_req["thinking"] = {"type": "disabled"}

        return chat_req
