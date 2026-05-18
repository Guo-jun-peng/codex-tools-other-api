"""豆包 (Doubao) 适配器 —— 火山引擎 Ark API"""

from .base import BaseAdapter


class DoubaoAdapter(BaseAdapter):
    name = "doubao"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    api_key_env = "ARK_API_KEY"

    def preprocess_image_gen_request(self, req: dict) -> dict:
        req.setdefault("response_format", "url")
        if "watermark" not in req:
            req["watermark"] = False
        return req

    def preprocess_chat_request(self, chat_req: dict) -> dict:
        super().preprocess_chat_request(chat_req)

        stop = chat_req.get("stop")
        if isinstance(stop, list) and len(stop) > 4:
            chat_req["stop"] = stop[:4]

        return chat_req
