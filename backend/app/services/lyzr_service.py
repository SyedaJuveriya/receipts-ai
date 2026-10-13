
import httpx

from app.core.config import settings


class LyzrService:
    def __init__(self) -> None:
        self.api_key = settings.lyzr_api_key
        self.agent_id = settings.lyzr_agent_id
        self.api_url = settings.lyzr_api_url

    async def extract_memories(
        self,
        message: str,
        user_id: str = "receipts-user",
        session_id: str = "receipts-session",
    ) -> dict:
        if not self.api_key or not self.agent_id:
            raise RuntimeError("Lyzr API key or agent ID is missing")

        payload = {
            "user_id": user_id,
            "agent_id": self.agent_id,
            "session_id": session_id,
            "message": message,
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload,
            )
            print("Lyzr response:", response.status_code, response.text)
            response.raise_for_status()
            return response.json()


lyzr_service = LyzrService()
