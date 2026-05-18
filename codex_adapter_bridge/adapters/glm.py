"""智谱 GLM 适配器"""

from .base import BaseAdapter


class GlmAdapter(BaseAdapter):
    name = "zhipu"
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    api_key_env = "ZHIPU_API_KEY"

    def preprocess_chat_request(self, chat_req: dict) -> dict:
        super().preprocess_chat_request(chat_req)

        if "thinking" not in chat_req:
            chat_req["thinking"] = {"type": "disabled"}

        if "do_sample" not in chat_req:
            chat_req["do_sample"] = True

        return chat_req
