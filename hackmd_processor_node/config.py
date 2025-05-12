from pydantic import Field
from koi_net.config import NodeConfig, KoiNetConfig
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides


class ProcessorNodeConfig(NodeConfig):
    """Configuration for the HackMD Processor Node."""

    koi_net: KoiNetConfig = Field(
        default_factory=lambda: KoiNetConfig(
            node_name="processor_hackmd",
            node_profile=NodeProfile(
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[], state=[]
                ),
            ),
        )
    )

    # Configure fetch retry settings
    fetch_retry_initial: int = Field(default=30, description="Initial backoff in seconds")
    fetch_retry_multiplier: int = Field(default=2, description="Backoff multiplier for retries")
    fetch_retry_max_attempts: int = Field(default=3, description="Maximum retry attempts")
    index_db_path: str = Field(default=".koi/index_db/index.db", description="Path to the SQLite index database file")
