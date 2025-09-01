from models.base import BaseSchemaModel
from typing import List, Union, Optional
from semantic_kernel.contents import ChatMessageContent


class AskAIRequest(BaseSchemaModel):
    messages: Optional[Union[str, dict, List[Union[str, dict]]]] = None
    system: Optional[str] = None
    language_code: Optional[str] = None
    temperature: float = 0.7
    maxTokens: int = 512

    def normalized_messages(self) -> List[ChatMessageContent]:
        if not self.messages:
            return []
        raw = self.messages if isinstance(self.messages, list) else [self.messages]

        norm = []
        for item in raw:
            if isinstance(item, dict) and item.get("content"):
                norm.append(ChatMessageContent(role=item.get("role", "user"), content=str(item["content"])))
            elif isinstance(item, str) and item.strip():
                norm.append(ChatMessageContent(role="user", content=item.strip()))
        return norm