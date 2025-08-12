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
        return f"General plugin received user input: {user_input}"

    @kernel_function(description="Provide general help and available capabilities.")
    def general_help(self, _user_input: str = "") -> Dict[str, Any]:
        # _user_input is intentionally unused; kept for backward-compatible signature
        return self._format_response(
            "I can help with remote access, safety & emergency, charging & energy, vehicle features, diagnostics, and alerts.",
            data={
                "capabilities": [
                    "remote_access", "safety_emergency", "charging_energy",
                    "vehicle_feature_control", "diagnostics_battery", "alerts_notifications"
                ]
            }
        )