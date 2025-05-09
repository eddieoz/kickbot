import logging
import sys

from .kick_bot import KickBot
from .kick_message import KickMessage
from .kick_webhook_handler import KickWebhookHandler
from .kick_signature_verifier import KickSignatureVerifier

time_format = "%Y-%m-%d %I:%M.%S %p"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)

formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt=time_format)
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
