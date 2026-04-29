from gateway.config.models import XYZEnvelope
from gateway.service.chat_service import ChatService


class ClusterInsightsService:
    """
    this class should inherit the protobuffs for the insights pipleine. similiar ot the Grader Service
    refer to colab and docs.
    A new proto will be needed
    """

    async def ClusterInsights(self):
        # Call ChatService from here.
        pass


        # XYZ is a dummy evenlope of typ eenvelope. It should be apyndatic class that defines how the llm should respond
        # Refer to file: gateway/config/models.py


        await ChatService().chat(
            system_prompt="from backend",
            user_prompt="from backend",
            model_name="from backend",
            job_id="from backend",
            trace_id="bfrom abckend",
            envelope_model=XYZEnvelope
        )