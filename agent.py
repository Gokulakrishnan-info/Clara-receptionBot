import os
import boto3
from livekit.plugins import bedrock

from dotenv import load_dotenv
import logging
from logging import handlers
import threading
import asyncio
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation, google, tavus
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from face_recognition import start_face_greeting, retry_face_recognition, reset_face_recognition_state, new_user_detected, register_employee_face, request_employee_face_registration, complete_employee_face_registration
from Modules.tools_registry import (
    get_weather,
    send_email,
    search_web,
    listen_for_commands,
    company_info,
    get_employee_details,
    get_my_employee_info,
    get_employee_by_name,
    get_employee_field,
    who_am_i,
    get_candidate_details,
    log_and_notify_visitor,
    set_role,
)
# Load environment variables
load_dotenv()
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Configure logging: console + rotating file with timestamps
os.makedirs(os.path.join("KMS", "logs"), exist_ok=True)
log_file_path = os.path.join("KMS", "logs", "agent.log")

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Formatter
_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
formatter = logging.Formatter(_fmt)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)

# File handler (rotating)
fh = handlers.RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)

# Avoid duplicate handlers in reloads
if not root_logger.handlers:
    root_logger.addHandler(ch)
    root_logger.addHandler(fh)
else:
    # Replace existing handlers with our configured ones
    root_logger.handlers = [ch, fh]

# Increase verbosity for livekit and tools
logging.getLogger("livekit").setLevel(logging.DEBUG)
logging.getLogger("livekit.agents").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class Assistant(Agent):
    def __init__(self) -> None:
        #Create Google Realtime model with version compatibility (new/old plugin APIs)
        def _create_google_model():
            try:
                logger.info("Initializing Google RealtimeModel with manual_function_calls=True (new API)…")
                return google.beta.realtime.RealtimeModel(
                    voice="Aoede",
                    temperature=0.2,
                    manual_function_calls=True,
                )
            except TypeError:
                logger.info("Falling back to Google RealtimeModel without manual_function_calls (older API)…")
                return google.beta.realtime.RealtimeModel(
                    voice="Aoede",
                    temperature=0.2,
                )

        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=_create_google_model(),
            tools=[
                company_info,
                get_employee_details,
                get_my_employee_info,
                get_employee_by_name,
                get_employee_field,
                who_am_i,
                get_candidate_details,
                listen_for_commands,
                set_role,
                start_face_greeting,
                retry_face_recognition,
                request_employee_face_registration,
                complete_employee_face_registration,
                register_employee_face,
                new_user_detected,
                get_weather,
                search_web,
                send_email,
                log_and_notify_visitor,
            ],
        )
        logger.info("Assistant initialized with tools: %s", [t.__name__ for t in self.tools])


        #Create Bedrock Realtime model
        # def _create_bedrock_model():
        #     try:
        #         logger.info("Initializing Bedrock RealtimeModel (Claude 3 Haiku)…")

        #         boto3_client = boto3.client(
        #             "bedrock-runtime",
        #             region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        #         )

        #         return bedrock.RealtimeModel(
        #             model_id="anthropic.claude-3-haiku-20240307-v1:0",  # fast + cost effective
        #             client=boto3_client,
        #             temperature=0.3,
        #         )
        #     except Exception as e:
        #         logger.exception("Failed to initialize Bedrock model: %s", e)
        #         raise

        # super().__init__(
        #     instructions=AGENT_INSTRUCTION,
        #     llm=_create_bedrock_model(),
        #     tools=[
        #         company_info,
        #         get_employee_details,
        #         get_my_employee_info,
        #         get_employee_by_name,
        #         get_employee_field,
        #         who_am_i,
        #         get_candidate_details,
        #         listen_for_commands,
        #         set_role,
        #         start_face_greeting,
        #         retry_face_recognition,
        #         request_employee_face_registration,
        #         complete_employee_face_registration,
        #         register_employee_face,
        #         new_user_detected,
        #         get_weather,
        #         search_web,
        #         send_email,
        #         log_and_notify_visitor,
        #     ],
        # )
        # logger.info("Assistant initialized with tools: %s", [t.__name__ for t in self.tools])

async def entrypoint(ctx: agents.JobContext):
    # Initialize AgentSession
    session = AgentSession()
    logger.info("Agent session created. Connecting to room…")

    # # Initialize Tavus AvatarSession
    # avatar = tavus.AvatarSession(
    #     replica_id=os.environ.get("REPLICA_ID"),
    #     persona_id=os.environ.get("PERSONA_ID"),
    #     api_key=os.environ.get("TAVUS_API_KEY"),
    # )

    # # Debug prints for environment variables
    # print("PERSONA_ID:", os.environ.get("PERSONA_ID"))
    # print("REPLICA_ID:", os.environ.get("REPLICA_ID"))
    # print("TAVUS_API_KEY:", os.environ.get("TAVUS_API_KEY"))

    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Correct RoomInputOptions
    room_options = RoomInputOptions(
        video_enabled=True,
        noise_cancellation=noise_cancellation.BVC(),
        # close_on_disconnect=False
    )

    # Start the Agent session
    try:
        await session.start(
            room=ctx.room,
            agent=Assistant(),
            room_input_options=room_options,
        )
        logger.info("Agent session started successfully.")
    except Exception as e:
        logger.exception("Failed to start agent session: %s", e)
        raise

    # Connect context
    try:
        await ctx.connect()
        logger.info("Job context connected.")
    except Exception as e:
        logger.exception("Failed to connect job context: %s", e)
        raise

    # Reset face recognition state for new session
    reset_face_recognition_state()
    logger.info("Face recognition state reset.")

    # Start with standard greeting - user should say "hey clara" to start face recognition
    logger.info("Sending initial SESSION_INSTRUCTION to LLM…")
    try:
        await session.generate_reply(
            instructions=SESSION_INSTRUCTION,
        )
        logger.info("Initial instruction delivered to LLM.")
    except Exception as e:
        logger.exception("generate_reply failed: %s", e)
        raise


# Print Tavus API key at startup (for debug)
print("Tavus API Key being used:", os.getenv("TAVUS_API_KEY"))

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )
