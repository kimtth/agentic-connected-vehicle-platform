import json
from typing import Dict, Any
from semantic_kernel.functions import kernel_function

class GeneralPlugin:
    @kernel_function(
        description="General plugin for vehicle inquiries."
    )
    def _general_plugin(self, user_input: str) -> str:
        return f"General plugin received user input: {user_input}"