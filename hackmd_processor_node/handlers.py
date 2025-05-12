import logging
from rid_types import HackMDNote
from koi_net.processor.handler import HandlerType, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.processor.interface import ProcessorInterface
from koi_net.protocol.event import EventType
from koi_net.protocol.node import NodeProfile
from koi_net.protocol.edge import EdgeType
from koi_net.protocol.helpers import generate_edge_bundle
from rid_lib.types import KoiNetNode, KoiNetEdge

from .core import node
from .note import note_service

logger = logging.getLogger(__name__)

# --- Network handler: discover Sensors providing HackMDNote -------------
@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handle_network_discovery(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    Discover sensors that provide HackMDNote, propose edge, and fetch historical bundles.
    """
    if kobj.normalized_event_type != EventType.NEW:
        return

    # Skip internal events
    if kobj.source != KnowledgeSource.External:
        return

    bundle = kobj.bundle
    if bundle is None:
        return

    try:
        profile: NodeProfile = bundle.validate_contents(NodeProfile)

        # Check if this node provides HackMDNote
        if HackMDNote not in profile.provides.event:
            return  # not a HackMD Sensor

        logger.info(f"HackMD Sensor discovered - requesting subscription to {kobj.rid}")
        if isinstance(kobj.rid, KoiNetNode):
            edge_bundle = generate_edge_bundle(
                source=proc.identity.rid,
                target=kobj.rid,
                edge_type=EdgeType.WEBHOOK,
                rid_types=[HackMDNote],
            )
            proc.handle(bundle=edge_bundle)

        # Cold-start catch-up (fetch all historical notes from sensor)
        try:
            logger.info(f"Fetching historical notes from sensor {kobj.rid}")
            rid_payload = proc.network.request_handler.fetch_rids(kobj.rid, rid_types=[HackMDNote])
            if rid_payload and rid_payload.rids:
                logger.info(f"Found {len(rid_payload.rids)} historical notes")
                bundle_payload = proc.network.request_handler.fetch_bundles(kobj.rid, rids=rid_payload.rids)
                for bundle in bundle_payload.bundles:
                    proc.handle(bundle=bundle, source=KnowledgeSource.External)
        except Exception as e:
            logger.error(f"Error fetching historical notes: {e}")
    except Exception as e:
        logger.error(f"Error processing node {kobj.rid}: {e}")

    return kobj

# --- Manifest handler: handle note manifest and trigger bundle fetch ----
@node.processor.register_handler(HandlerType.Manifest, rid_types=[HackMDNote])
def handle_note_manifest(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    On incoming HackMDNote manifest, trigger bundle fetch from a state provider.
    """
    logger.info(f"Handling manifest for note {kobj.rid}")

    # If we already have the contents, skip fetch
    if kobj.contents is not None:
        logger.debug("Bundle already present, skipping fetch attempt.")
        return kobj

    # Let the pipeline handle bundle fetching
    logger.debug(f"Manifest for {kobj.rid} received, relying on pipeline to fetch bundle.")
    return kobj

# --- Bundle handler: index notes ---------------------------------------
@node.processor.register_handler(HandlerType.Bundle, rid_types=[HackMDNote])
def handle_note_bundle(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    Compare hashes; set normalized_event_type to NEW or UPDATE; perform indexing of note content.
    """
    logger.info(f"Processing bundle for note {kobj.rid}")

    # Check for existing note and compare hashes
    prev = proc.cache.read(kobj.rid)
    is_update = prev is not None
    if prev and prev.manifest and kobj.manifest:
        hash_changed = prev.manifest.sha256_hash != kobj.manifest.sha256_hash
    else:
        hash_changed = True

    if is_update and not hash_changed:
        logger.info(f"Note {kobj.rid} unchanged (same hash), skipping indexing")
        return STOP_CHAIN

    # Set the normalized event type
    kobj.normalized_event_type = EventType.UPDATE if is_update else EventType.NEW
    event_type_str = "updated" if is_update else "new"
    logger.info(f"Processing {event_type_str} note {kobj.rid}")

    # Extract data from the bundle contents
    bundle = kobj.bundle
    if not bundle:
        logger.error(f"No bundle available for {kobj.rid}")
        return kobj

    contents = bundle.contents
    if not contents:
        logger.error(f"Empty bundle contents for {kobj.rid}")
        return kobj

    try:
        # Index the note in our database
        if isinstance(kobj.rid, HackMDNote):
            # Add hash to contents for tracking
            if kobj.manifest:
                contents["_koi_manifest_hash"] = kobj.manifest.sha256_hash
            else:
                contents["_koi_manifest_hash"] = None
            contents["_koi_bundle_rid"] = str(kobj.rid)

            # Process and index the note bundle
            success = note_service.process_note_bundle(
                rid=kobj.rid,
                bundle_data=contents,
                event_type=event_type_str.upper()
            )

            if success:
                logger.info(f"Successfully indexed {event_type_str} note {kobj.rid}")
            else:
                logger.warning(f"Failed to index {event_type_str} note {kobj.rid}")
    except Exception as e:
        logger.error(f"Error indexing note {kobj.rid}: {e}")

    return kobj

# --- Network handler: edges negotiation -------------------------------
@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetEdge])
def handle_edge_negotiation(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    Handle edge negotiation responses from sensors.
    This ensures connections are properly established and tracked.
    """
    logger.debug(f"Processing edge: {kobj.rid}")

    # Only process edges that are responses to our subscription requests
    if kobj.source != KnowledgeSource.External:
        return

    try:
        # Extract edge details from bundle
        bundle = kobj.bundle
        if not bundle:
            return

        edge = bundle.contents

        # Check if this is an edge approval targeting us
        if (edge.get("target") == str(proc.identity.rid) and
            edge.get("status") == "approved"):

            sensor_rid = edge.get("source")
            logger.info(f"Edge approved by sensor {sensor_rid} for HackMD notes")

    except Exception as e:
        logger.error(f"Error processing edge: {e}")

    return kobj
