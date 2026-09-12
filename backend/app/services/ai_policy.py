import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ai_model_key import AiModelKey
from app.config import settings

class AIService:
    """AI服务类，处理DeepSeek调用"""
    
    def __init__(self, db: AsyncSession, team_id: int):
        self.db = db
        self.team_id = team_id
        self.client = httpx.AsyncClient(
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=30.0
        )
    
    async def get_api_key(self) -> str:
        """获取团队的DeepSeek API Key"""
        result = await self.db.execute(
            select(AiModelKey).where(
                AiModelKey.team_id == self.team_id,
                AiModelKey.service == "deepseek",
                AiModelKey.is_active == True
            ).limit(1)
        )
        key_record = result.scalar_one_or_none()
        if not key_record:
            # 尝试使用系统级Key（如果配置了环境变量）
            if settings.DEEPSEEK_API_KEY:
                return settings.DEEPSEEK_API_KEY
            raise ValueError("未配置DeepSeek API Key")
        return key_record.api_key
    
    async def generate_content(self, prompt: str, temperature: float = 0.5, max_tokens: int = 800) -> dict:
        """调用DeepSeek生成内容"""
        api_key = await self.get_api_key()
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个专业的科研申报辅导专家。请根据用户提供的信息，生成高质量的申报材料内容。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = await self.client.post("/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            return {
                "content": result["choices"][0]["message"]["content"],
                "model": result.get("model", "deepseek-chat"),
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                "success": True
            }
        except httpx.HTTPStatusError as e:
            return {
                "content": f"API调用失败: {e.response.status_code}",
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            return {
                "content": f"生成失败: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        await self.client.aclose()
