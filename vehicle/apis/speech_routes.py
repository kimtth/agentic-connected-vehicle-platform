import os
import time
import requests
from fastapi import APIRouter, HTTPException
from models.api_request import AskAIRequest
from models.api_responses import AIResponse, SpeechTokenResponse, GenericPayloadResponse
from plugin.oai_service import create_chat_service
from semantic_kernel.agents import ChatCompletionAgent

router = APIRouter(prefix="/speech", tags=["Speech"])

# Simple in-memory token cache (Speech tokens valid ~10 min)
_TOKEN_CACHE = {"token": None, "expires": 0, "region": None}


def _issue_speech_token():
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not speech_region:
        raise HTTPException(status_code=500, detail="Speech key/region not configured")
    url = f"https://{speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": speech_key}
    try:
        resp = requests.post(url, headers=headers, timeout=5)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Speech service: {exc}"
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    # Cache for 9 minutes (token lifetime 10 minutes)
    _TOKEN_CACHE.update(
        {"token": resp.text, "expires": time.time() + 9 * 60, "region": speech_region}
    )


def _issue_ice_token():
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not speech_region:
        raise HTTPException(status_code=500, detail="Speech key/region not configured")
    url = f"https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1"
    headers = {"Accept": "application/json", "Ocp-Apim-Subscription-Key": speech_key}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach ICE token service: {exc}"
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    try:
        return resp.json()
    except ValueError:
        raise HTTPException(
            status_code=502, detail="Invalid JSON response from ICE token service"
        )


def _get_cached_token():
    if time.time() >= _TOKEN_CACHE["expires"] or not _TOKEN_CACHE["token"]:
        _issue_speech_token()
    return {"token": _TOKEN_CACHE["token"], "region": _TOKEN_CACHE["region"]}


@router.get("/token", response_model=SpeechTokenResponse)
def speech_token():
    """Alias route to match frontend expectation (/api/speech/token)."""
    cached = _get_cached_token()
    return SpeechTokenResponse(**cached)


@router.get("/ice_token", response_model=GenericPayloadResponse)
def speech_ice_token():
    return GenericPayloadResponse(payload=_issue_ice_token())


@router.post("/ask_ai", response_model=AIResponse)
async def ask_ai(req: AskAIRequest):
    """
    Direct AI response using Semantic Kernel ChatCompletionAgent.
    Supports conversation history and vehicle context.
    Accepts optional language_code from client to localize response.
    """
    try:
        service = create_chat_service()
        language_code = req.language_code  # Provided by frontend (auto-detected)

        # Enhanced system prompt for vehicle context
        system_prompt = (
            req.system
            or """You are a helpful AI assistant for a connected vehicle platform.
                You assist users with vehicle operations, diagnostics, navigation, and general inquiries.
                Keep responses concise and actionable. When asked about vehicle-specific features, provide practical guidance.

                Do not add highlight entries — this text will be used for text-to-speech.

                The response should be simple and not longer than 90 characters.
                """
        )
        if language_code:
            system_prompt += f"{os.linesep} Please respond in {language_code}."

        agent = ChatCompletionAgent(
            service=service,
            name="VehicleAssistant",
            instructions=system_prompt,
        )

        messages = req.normalized_messages()
        if not messages:
            raise HTTPException(status_code=400, detail="Empty message payload")

        sk_response = await agent.get_response(messages=messages)

        # Safely extract message/content from Semantic Kernel response.
        message_obj = getattr(sk_response, "message", None)
        if message_obj is None:
            # Fallback to string representation of the response
            response_text = str(sk_response).strip()
        else:
            content = getattr(message_obj, "content", "") or str(message_obj)
            role = getattr(message_obj, "role", "").lower() if getattr(message_obj, "role", None) else ""
            response_text = content.strip()

            if role == "system" and response_text:
                response_text = response_text

        if not response_text:
            raise HTTPException(status_code=502, detail="Empty response from AI service")

        return AIResponse(response=response_text)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI request failed: {e}")
