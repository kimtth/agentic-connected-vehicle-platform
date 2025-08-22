from typing import Dict, Any
from semantic_kernel.functions import kernel_function

# Try to reuse shared formatting helpers
try:
    from agents.base.base_agent import BasePlugin as _BasePlugin
except Exception:
    class _BasePlugin:
        def _format_response(self, message: str, success: bool = True, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
            return {"message": message, "success": success, "data": data or {}}

class GeneralPlugin(_BasePlugin):
    @kernel_function(
        description="General plugin for vehicle inquiries."
    )
    def _general_plugin(self, user_input: str) -> str:
        """Process general vehicle inquiries and return a formatted response."""
        if not user_input or not isinstance(user_input, str):
            return "I need more information to help you. Please provide a specific question about your vehicle."
        
        return f"General plugin received user input: {user_input.strip()}"

    @kernel_function(description="Provide general help and available capabilities.")
    def general_help(self, _user_input: str = "") -> Dict[str, Any]:
        """Provide help information about available vehicle capabilities."""
        # _user_input is intentionally unused; kept for backward-compatible signature
        try:
            return self._format_response(
                "I can help with remote access, safety & emergency, charging & energy, vehicle features, diagnostics, and alerts.",
                data={
                    "capabilities": [
                        "remote_access", "safety_emergency", "charging_energy",
                        "vehicle_feature_control", "diagnostics_battery", "alerts_notifications"
                    ]
                }
            )
        except Exception as e:
            # Ensure we always return a valid response even if formatting fails
            return {
                "message": "Help information available - contact support for assistance",
                "success": False,
                "error": str(e),
                "data": {}
            }