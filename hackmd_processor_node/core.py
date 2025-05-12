import logging
from koi_net import NodeInterface
from .config import ProcessorNodeConfig

# Set up logging
logger = logging.getLogger(__name__)

# Initialize the KOI-net Node Interface
node = NodeInterface(
    config=ProcessorNodeConfig.load_from_yaml("config.yaml"),
    use_kobj_processor_thread=True,
)

logger.info(f"Initialized NodeInterface: {node.identity.rid}")
assert node.config.server is not None, "server config missing"
logger.info(f"Node base URL: {node.config.server.url}")
logger.info(f"Node attempting first contact with: {node.config.koi_net.first_contact}")

# Import handlers after node is initialized
from . import handlers 