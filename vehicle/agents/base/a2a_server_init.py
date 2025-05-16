from agents.base.a2a_task_manager import TaskManager
from agents.a2a_common.server import A2AServer
from agents.a2a_common.types import AgentCapabilities, AgentCard, AgentSkill
from agents.a2a_common.utils.push_notification_auth import PushNotificationSenderAuth
from utils.logging_config import get_logger

logger = get_logger(__name__)


def start_a2a_server(host: str = 'localhost', port: int = 10020):
    """Starts the Semantic Kernel Agent server using A2A."""
    logger.info("Starting A2A server for Semantic Kernel Agent...")
    # Build the agent card
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill_trip_planning = AgentSkill(
        id='trip_planning_sk',
        name='Semantic Kernel Trip Planning',
        description=(
            'Handles comprehensive trip planning, including currency exchanges, itinerary creation, sightseeing, '
            'dining recommendations, and event bookings using Frankfurter API for currency conversions.'
        ),
        tags=['trip', 'planning', 'travel', 'currency', 'semantic-kernel'],
        examples=[
            'Plan a budget-friendly day trip to Seoul including currency exchange.',
            "What's the exchange rate and recommended itinerary for visiting Tokyo?",
        ],
    )

    agent_card = AgentCard(
        name='SK Travel Agent',
        description=(
            'Semantic Kernel-based travel agent providing comprehensive trip planning services '
            'including currency exchange and personalized activity planning.'
        ),
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=capabilities,
        skills=[skill_trip_planning],
    )

    # Prepare push notification system
    notification_sender_auth = PushNotificationSenderAuth()
    notification_sender_auth.generate_jwk()

    # Create the server
    task_manager = TaskManager(
        notification_sender_auth=notification_sender_auth
    )
    server = A2AServer(
        agent_card=agent_card, task_manager=task_manager, host=host, port=port
    )
    server.app.add_route(
        '/.well-known/jwks.json',
        notification_sender_auth.handle_jwks_endpoint,
        methods=['GET'],
    )
    server.start()
    logger.info("A2A server started successfully.")

