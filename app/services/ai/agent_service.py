from app.di.container import container
from dependency_injector.wiring import inject, Provide
from openai import AsyncOpenAI
import google.generativeai as genai
from app.services.ai.rag_service import RAGService
from app.services.ai.memory_service import MemoryService
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.guardrails_service import GuardrailsService
from structlog import get_logger

logger = get_logger(__name__)


class AgentService:
    @inject
    def __init__(
        self,
        rag = Provide["rag_service"],
        memory = Provide["memory_service"],
        prompt_builder = Provide["prompt_builder"],
        guardrails = Provide["guardrails_service"],
        openai = Provide["openai_client"],
        gemini_client = Provide["gemini_client"],
    ):
        self.rag = rag
        self.memory = memory
        self.prompt_builder = prompt_builder
        self.guardrails = guardrails
        self.openai = openai
        self.gemini_client = gemini_client

    async def process_message(
        self,
        conversation_id: str,
        config: dict,
        message: str,
    ) -> tuple[str, float]:
        """Returns (response_text, confidence_score)"""
        try:
            logger.info(f"AgentService: Processing message for conversation {conversation_id}...")

            # 1. Load conversation history from Redis
            history = await self.memory.get_history(conversation_id)

            # 2. Retrieve relevant knowledge from PostgreSQL + pgvector
            knowledge = await self.rag.retrieve(
                query=message,
                top_k=5,
            )

            # 3. Build system prompt dynamically
            system_prompt = self.prompt_builder.build(
                persona_name=config.get("persona_name", "Assistant"),
                business_name=config.get("business_name", ""),
                tone=config.get("tone", "friendly and professional"),
                knowledge_context=knowledge,
                hard_rules=config.get("hard_rules", []),
            )

            # 4. LLM inference - use Gemini or OpenAI based on config
            use_gemini = config.get("use_gemini", False)

            if use_gemini and self.gemini_client:
                # Build conversation history for Gemini
                gemini_history = []
                for msg in history:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role": role, "parts": [msg["content"]]})

                # Start chat with history
                chat = self.gemini_client.start_chat(history=gemini_history)

                # Combine system prompt with user message for Gemini
                full_message = f"{system_prompt}\n\nUser: {message}"

                response = await chat.send_message_async(
                    full_message,
                    generation_config=genai.types.GenerationConfig(
                        temperature=config.get("temperature", 0.7),
                        max_output_tokens=config.get("max_tokens", 800),
                    )
                )

                raw_response = response.text
                tokens_used = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
            elif self.openai:
                response = await self.openai.chat.completions.create(
                    model=config.get("model", "gpt-4o"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *history,
                        {"role": "user", "content": message},
                    ],
                    temperature=config.get("temperature", 0.7),
                    max_tokens=config.get("max_tokens", 800),
                )

                raw_response = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
            else:
                raise ValueError("No AI client configured")

            # 5. Run guardrails (safety + confidence check)
            safe_response, confidence = await self.guardrails.validate(
                response=raw_response,
                config=config,
            )

            # 6. Save response to memory
            await self.memory.append(conversation_id, "assistant", safe_response)

            logger.info(f"AgentService: AI response generated for conversation {conversation_id}", extra={
                "tokens_used": tokens_used,
                "confidence": confidence,
                "provider": "gemini" if use_gemini else "openai",
            })

            return safe_response, confidence

        except Exception as e:
            logger.error(f"AgentService: Failed to process message for conversation {conversation_id}.", exc_info=True)
            raise e
