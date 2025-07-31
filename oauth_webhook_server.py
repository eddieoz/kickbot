#!/usr/bin/env python3
"""
Unified Webhook Server for KickBot (Story 2)
This server handles OAuth callbacks and Kick API webhook events on port 8080
Integrates with bot instance for command processing and includes signature verification
"""

import asyncio
import os
import sys
from pathlib import Path
from aiohttp import web
from urllib.parse import parse_qs, quote_plus
import logging
import json
from datetime import datetime
import aiohttp
from typing import Optional, Dict, Any

# Load .env manually since python-dotenv might not be available
def load_env_file(env_path='.env'):
    """Manually load environment variables from .env file"""
    env_file = Path(env_path)
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Load environment variables
load_env_file()

try:
    from kickbot.kick_auth_manager import KickAuthManager
    from kickbot.kick_signature_verifier import KickSignatureVerifier
    from kickbot.kick_message import KickMessage
except ImportError:
    # Add current directory to path if import fails
    sys.path.insert(0, '.')
    from kickbot.kick_auth_manager import KickAuthManager
    from kickbot.kick_signature_verifier import KickSignatureVerifier
    from kickbot.kick_message import KickMessage

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables
auth_manager = None
signature_verifier = None
bot_instance = None
chat_correlator = None
webhook_monitor = None
webhook_diagnostics = None
enable_signature_verification = False

# Message deduplication system
import time
processed_messages = {}  # message_id -> timestamp
DEDUP_WINDOW_SECONDS = 30  # Ignore duplicates within 30 seconds

# Load settings for alerts
try:
    with open('settings.json', 'r') as f:
        settings = json.load(f)
except Exception as e:
    logger.error(f"Failed to load settings.json: {e}")
    settings = {}

# ==================== STORY 15: MONITORING CLASSES ====================

class WebhookMonitoring:
    """
    Comprehensive monitoring and metrics tracking for webhook processing (Story 15)
    
    Tracks success/failure rates, performance metrics, and provides alerting
    capabilities for webhook processing system health.
    """
    
    def __init__(self):
        """Initialize monitoring with zero metrics"""
        self.metrics = {
            'webhook_received': 0,
            'parsing_success': 0,
            'parsing_failure': 0,
            'correlation_success': 0,
            'correlation_timeout': 0,
            'correlation_failure': 0,
            'points_awarded': 0,
            'anonymous_gifts': 0,
            'empty_payloads': 0
        }
        
        # Detailed tracking data
        self.event_type_counts = {}
        self.parsing_method_counts = {}
        self.failure_reasons = []
        self.correlation_timings = []
        self.timeout_webhooks = []
        self.performance_metrics = {}
        self.alert_thresholds = {}
        self.error_log = []
        self.total_points_awarded = 0
        self.total_anonymous_subscriptions = 0
        
        self.logger = logging.getLogger(__name__)
        
    def track_webhook_received(self, event_type):
        """Track webhook reception by event type"""
        self.metrics['webhook_received'] += 1
        self.event_type_counts[event_type] = self.event_type_counts.get(event_type, 0) + 1
        self.logger.info(f"📊 MONITOR: Webhook received - {event_type} (total: {self.metrics['webhook_received']})")
        
    def track_parsing_success(self, gifter, method):
        """Track successful webhook parsing"""
        self.metrics['parsing_success'] += 1
        self.parsing_method_counts[method] = self.parsing_method_counts.get(method, 0) + 1
        self.logger.info(f"📊 MONITOR: Parsing success - {gifter} via {method}")
        
    def track_parsing_failure(self, payload, error_msg):
        """Track webhook parsing failures with detailed context"""
        self.metrics['parsing_failure'] += 1
        
        failure_info = {
            'timestamp': time.time(),
            'payload': str(payload)[:200],  # Truncate large payloads
            'error': error_msg,
            'payload_type': type(payload).__name__
        }
        self.failure_reasons.append(failure_info)
        
        # Track empty payloads specifically (only empty dict, not None)
        if payload == {}:
            self.metrics['empty_payloads'] += 1
            
        self.logger.error(f"📊 MONITOR: Parsing failure - {error_msg} (payload: {str(payload)[:100]})")
        
    def track_correlation_success(self, gifter, quantity, delay):
        """Track successful webhook-to-chat correlation"""
        self.metrics['correlation_success'] += 1
        
        correlation_data = {
            'timestamp': time.time(),
            'gifter': gifter,
            'quantity': quantity,
            'delay': delay
        }
        self.correlation_timings.append(correlation_data)
        
        self.logger.info(f"📊 MONITOR: Correlation success - {gifter} (delay: {delay:.1f}s)")
        
    def track_correlation_timeout(self, webhook_data):
        """Track correlation timeouts"""
        self.metrics['correlation_timeout'] += 1
        
        timeout_info = {
            'timestamp': time.time(),
            'webhook_id': webhook_data.get('event_id', 'unknown'),
            'webhook_timestamp': webhook_data.get('timestamp', 0)
        }
        self.timeout_webhooks.append(timeout_info)
        
        self.logger.warning(f"📊 MONITOR: Correlation timeout - {webhook_data.get('event_id', 'unknown')}")
        
    def track_points_awarded(self, gifter, points, quantity):
        """Track points awarded to gifters"""
        self.metrics['points_awarded'] += 1
        self.total_points_awarded += points
        self.logger.info(f"📊 MONITOR: Points awarded - {gifter} received {points} points for {quantity} gifts")
        
    def track_anonymous_gift(self, quantity, scenario_type):
        """Track anonymous gift processing"""
        self.metrics['anonymous_gifts'] += 1
        self.total_anonymous_subscriptions += quantity
        self.logger.info(f"📊 MONITOR: Anonymous gift - {quantity} subscriptions ({scenario_type})")
        
    def track_performance(self, operation, duration):
        """Track performance metrics for operations"""
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = []
        self.performance_metrics[operation].append(duration)
        
    def track_error(self, error_type, error_msg):
        """Track general errors with categorization"""
        error_info = {
            'timestamp': time.time(),
            'error_type': error_type,
            'error_msg': error_msg
        }
        self.error_log.append(error_info)
        
    def set_alert_threshold(self, metric_name, threshold):
        """Set alert threshold for a metric"""
        self.alert_thresholds[metric_name] = threshold
        
    def check_alert_conditions(self):
        """Check if any alert conditions are triggered"""
        alerts = []
        
        # Check parsing failure rate
        if 'parsing_failure_rate' in self.alert_thresholds:
            total_webhooks = self.metrics['webhook_received']
            if total_webhooks > 0:
                failure_rate = self.metrics['parsing_failure'] / total_webhooks
                if failure_rate > self.alert_thresholds['parsing_failure_rate']:
                    alerts.append({
                        'type': 'parsing_failure_rate',
                        'current_rate': failure_rate,
                        'threshold': self.alert_thresholds['parsing_failure_rate'],
                        'severity': 'high'
                    })
        
        # Check correlation timeout rate
        if 'correlation_timeout_rate' in self.alert_thresholds:
            total_correlations = self.metrics['correlation_success'] + self.metrics['correlation_timeout']
            if total_correlations > 0:
                timeout_rate = self.metrics['correlation_timeout'] / total_correlations
                if timeout_rate > self.alert_thresholds['correlation_timeout_rate']:
                    alerts.append({
                        'type': 'correlation_timeout_rate',
                        'current_rate': timeout_rate,
                        'threshold': self.alert_thresholds['correlation_timeout_rate'],
                        'severity': 'medium'
                    })
        
        return alerts
        
    def get_average_correlation_time(self):
        """Calculate average correlation timing"""
        if not self.correlation_timings:
            return 0.0
        return sum(timing['delay'] for timing in self.correlation_timings) / len(self.correlation_timings)
        
    def get_total_points_awarded(self):
        """Get total points awarded across all gifters"""
        return self.total_points_awarded
        
    def get_total_anonymous_subscriptions(self):
        """Get total anonymous subscriptions processed"""
        return self.total_anonymous_subscriptions
        
    def get_average_performance(self, operation):
        """Get average performance for an operation"""
        if operation not in self.performance_metrics:
            return 0.0
        timings = self.performance_metrics[operation]
        return sum(timings) / len(timings) if timings else 0.0
        
    def get_error_analysis(self):
        """Generate comprehensive error analysis"""
        error_categories = {}
        for error in self.error_log:
            error_type = error['error_type']
            error_categories[error_type] = error_categories.get(error_type, 0) + 1
            
        most_common_errors = sorted(
            [{'error_type': k, 'count': v} for k, v in error_categories.items()],
            key=lambda x: x['count'],
            reverse=True
        )
        
        return {
            'error_categories': error_categories,
            'most_common_errors': most_common_errors,
            'error_trends': {
                'total_errors': len(self.error_log),
                'recent_errors': len([e for e in self.error_log if time.time() - e['timestamp'] < 3600])
            }
        }
        
    def get_diagnostic_data(self):
        """Generate comprehensive diagnostic data"""
        return {
            'metrics_summary': self.metrics.copy(),
            'recent_activity': {
                'event_types': self.event_type_counts.copy(),
                'parsing_methods': self.parsing_method_counts.copy(),
                'recent_failures': self.failure_reasons[-10:],  # Last 10 failures
                'recent_timeouts': self.timeout_webhooks[-5:]   # Last 5 timeouts
            },
            'performance_stats': {
                operation: {
                    'count': len(timings),
                    'average': self.get_average_performance(operation),
                    'min': min(timings) if timings else 0,
                    'max': max(timings) if timings else 0
                }
                for operation, timings in self.performance_metrics.items()
            },
            'error_analysis': self.get_error_analysis(),
            'system_health': {
                'overall_status': self._calculate_system_health(),
                'correlation_avg_time': self.get_average_correlation_time(),
                'success_rates': {
                    'parsing': self._calculate_success_rate('parsing'),
                    'correlation': self._calculate_success_rate('correlation')
                }
            }
        }
        
    def _calculate_system_health(self):
        """Calculate overall system health status"""
        total_webhooks = self.metrics['webhook_received']
        if total_webhooks == 0:
            return 'unknown'
            
        parsing_success_rate = self.metrics['parsing_success'] / total_webhooks
        total_correlations = self.metrics['correlation_success'] + self.metrics['correlation_timeout']
        correlation_success_rate = self.metrics['correlation_success'] / total_correlations if total_correlations > 0 else 1.0
        
        if parsing_success_rate >= 0.9 and correlation_success_rate >= 0.8:
            return 'healthy'
        elif parsing_success_rate >= 0.7 and correlation_success_rate >= 0.6:
            return 'warning'
        else:
            return 'error'
            
    def _calculate_success_rate(self, category):
        """Calculate success rate for a category"""
        if category == 'parsing':
            total = self.metrics['parsing_success'] + self.metrics['parsing_failure']
            return self.metrics['parsing_success'] / total if total > 0 else 0.0
        elif category == 'correlation':
            total = self.metrics['correlation_success'] + self.metrics['correlation_timeout']
            return self.metrics['correlation_success'] / total if total > 0 else 0.0
        return 0.0


class WebhookDiagnostics:
    """
    Diagnostic endpoint handler for webhook system monitoring (Story 15)
    
    Provides HTTP endpoints for system health checking and diagnostic data access.
    """
    
    def __init__(self):
        self.monitor = None
        self.logger = logging.getLogger(__name__)
        
    def set_monitor(self, monitor):
        """Set the monitoring instance"""
        self.monitor = monitor
        
    async def handle_diagnostics_request(self, request):
        """Handle diagnostic endpoint requests"""
        try:
            if not self.monitor:
                return web.json_response({
                    'error': 'Monitoring system not available',
                    'status': 'error'
                }, status=503)
                
            # Get diagnostic data from monitor
            diagnostic_data = self.monitor.get_diagnostic_data()
            
            # Format for API response
            response_data = {
                'system_status': diagnostic_data.get('system_health', {}).get('overall_status', 'unknown'),
                'timestamp': time.time(),
                'metrics': diagnostic_data.get('metrics_summary', {}),
                'recent_errors': diagnostic_data.get('error_analysis', {}),
                'performance': diagnostic_data.get('performance_stats', {}),
                'correlation_stats': {
                    'average_time': diagnostic_data.get('system_health', {}).get('correlation_avg_time', 0.0),
                    'success_rate': diagnostic_data.get('system_health', {}).get('success_rates', {}).get('correlation', 0.0)
                },
                'recent_activity': diagnostic_data.get('recent_activity', {})
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            self.logger.error(f"❌ DIAGNOSTICS: Error generating diagnostic response: {e}")
            return web.json_response({
                'error': 'Failed to generate diagnostics',
                'status': 'error'
            }, status=500)

async def send_alert(img, audio, text, tts):
    """Send alert to the alert system"""
    if settings.get('Alerts', {}).get('Enable', False):
        try:
            async with aiohttp.ClientSession() as session:
                width = '300px'
                fontFamily = 'Arial'
                fontSize = 30
                color = 'gold'
                borderColor = 'black'
                borderWidth = 2
                duration = 9000
                parameters = f'/trigger_alert?gif={img}&audio={quote_plus(audio)}&text={text}&tts={tts}&width={width}&fontFamily={fontFamily}&fontSize={fontSize}&borderColor={borderColor}&borderWidth={borderWidth}&color={color}&duration={duration}'
                url = settings['Alerts']['Host'] + parameters + '&api_key=' + settings['Alerts']['ApiKey']
                async with session.get(url) as response:
                    response_text = await response.text()
                    logger.info(f"Alert sent successfully: {response.status}")
        except Exception as e:
            logger.error(f'Error sending alert: {e}')

class ExtractionResult:
    """
    Story 20: Comprehensive result object for username extraction
    Provides detailed information about the extraction process
    """
    def __init__(self, username, success, strategy_used=None, event_type=None, payload=None):
        self.username = username
        self.success = success
        self.strategy_used = strategy_used
        self.event_type = event_type
        self.payload = payload


class UnifiedUsernameExtractor:
    """
    Story 20: Unified, extensible username extraction utility
    Centralized system for extracting usernames from webhook payloads with strategy pattern
    """
    
    def __init__(self):
        """Initialize the extractor with default strategies"""
        self.strategies = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default extraction strategies for common event types"""
        
        # Follow event strategies
        self.register_strategy("follow", "follower.username", 
                             lambda data: data.get('follower', {}).get('username'))
        self.register_strategy("follow", "user.username",
                             lambda data: data.get('user', {}).get('username'))
        self.register_strategy("follow", "username",
                             lambda data: data.get('username'))
        
        # Subscription event strategies
        self.register_strategy("subscription", "subscriber.username",
                             lambda data: data.get('subscriber', {}).get('username'))
        self.register_strategy("subscription", "user.username",
                             lambda data: data.get('user', {}).get('username'))
        self.register_strategy("subscription", "username",
                             lambda data: data.get('username'))
        
        # Gift subscription event strategies
        self.register_strategy("gift_subscription", "gifter.username",
                             lambda data: data.get('gifter', {}).get('username'))
        self.register_strategy("gift_subscription", "user.username",
                             lambda data: data.get('user', {}).get('username'))
        self.register_strategy("gift_subscription", "username",
                             lambda data: data.get('username'))
    
    def register_strategy(self, event_type, strategy_name, strategy_func):
        """
        Register a new extraction strategy for an event type
        
        :param event_type: Type of event (follow, subscription, etc.)
        :param strategy_name: Human-readable name for the strategy
        :param strategy_func: Function that takes payload and returns username or None
        """
        if event_type not in self.strategies:
            self.strategies[event_type] = []
        
        self.strategies[event_type].append({
            'name': strategy_name,
            'func': strategy_func
        })
        
        logger.debug(f"Registered strategy '{strategy_name}' for event type '{event_type}'")
    
    def extract_username(self, payload, event_type):
        """
        Extract username from payload using registered strategies
        
        :param payload: Webhook payload data
        :param event_type: Type of event to determine which strategies to use
        :return: ExtractionResult object with extraction details
        """
        # Get strategies for this event type
        event_strategies = self.strategies.get(event_type, [])
        
        # If no specific strategies, try generic strategies
        if not event_strategies:
            event_strategies = self.strategies.get("follow", [])  # Use follow as fallback
        
        # Try each strategy in order
        for strategy in event_strategies:
            try:
                username = strategy['func'](payload)
                if self._is_valid_username(username):
                    logger.debug(f"Username '{username}' extracted using strategy '{strategy['name']}' for {event_type}")
                    return ExtractionResult(
                        username=username,
                        success=True,
                        strategy_used=strategy['name'],
                        event_type=event_type,
                        payload=payload
                    )
            except (KeyError, AttributeError, TypeError) as e:
                logger.debug(f"Strategy '{strategy['name']}' failed for {event_type}: {e}")
                continue
        
        # All strategies failed
        logger.warning(f"Failed to extract username from {event_type} payload: {payload}")
        return ExtractionResult(
            username="Unknown",
            success=False,
            strategy_used=None,
            event_type=event_type,
            payload=payload
        )
    
    def _is_valid_username(self, username):
        """
        Validate that a username is acceptable
        
        :param username: Username to validate
        :return: True if valid, False otherwise
        """
        if username is None:
            return False
        if not isinstance(username, str):
            return False
        if not username.strip():  # Empty or whitespace-only
            return False
        return True


# Global instance for backward compatibility and easy access
unified_extractor = UnifiedUsernameExtractor()


def extract_username_from_payload(event_data, event_type="follow"):
    """
    Story 20: Backward-compatible wrapper for the unified extractor
    Extract username from webhook payload using the unified extraction utility
    
    :param event_data: Webhook payload data
    :param event_type: Type of event (follow, subscription, etc.)
    :return: Username string (for backward compatibility)
    """
    result = unified_extractor.extract_username(event_data, event_type)
    return result.username

async def handle_follow_event(event_data):
    """Handle follow events with robust username extraction (Story 17)"""
    try:
        follower_name = extract_username_from_payload(event_data, "follow")
        logger.info(f"🎉 New follower: {follower_name}")
        
        # Send follow alert
        await send_alert(
            'https://media.giphy.com/media/3o6Zt6MLxUZV2LlqWc/giphy.gif',
            'https://www.myinstants.com/media/sounds/aplausos-efecto-de-sonido.mp3',
            f'Novo seguidor: {follower_name}!',
            f'Obrigado por seguir, {follower_name}!'
        )
    except Exception as e:
        logger.error(f"Error handling follow event: {e}")

def extract_tier_from_payload(event_data):
    """
    Story 18: Robust tier extraction with multiple strategies
    Extract subscription tier from webhook payload using multiple fallback strategies
    """
    tier_strategies = [
        lambda data: data.get('tier'),                          # Standard field
        lambda data: data.get('subscription_tier'),             # Alternative field  
        lambda data: data.get('level'),                         # Level field
        lambda data: data.get('subscription', {}).get('tier'),  # Nested structure
        lambda data: data.get('sub_tier'),                      # Another alternative
    ]
    
    for strategy in tier_strategies:
        try:
            tier = strategy(event_data)
            if tier is not None and isinstance(tier, (int, str)):
                tier_value = int(tier)
                if 1 <= tier_value <= 10:  # Reasonable tier range
                    logger.debug(f"Tier extracted: {tier_value}")
                    return tier_value
        except (KeyError, AttributeError, TypeError, ValueError):
            continue
    
    logger.debug("No tier found in payload, defaulting to tier 1")
    return 1  # Default tier

async def handle_subscription_event(event_data):
    """Handle subscription events with robust username and tier extraction (Story 18)"""
    try:
        subscriber_name = extract_username_from_payload(event_data, "subscription")
        tier = extract_tier_from_payload(event_data)
        logger.info(f"🎉 New subscription: {subscriber_name} (Tier {tier})")
        
        # Send subscription alert
        await send_alert(
            'https://media.tenor.com/0rEqnyTyZToAAAAC/eu-sou-rica-im-rich.gif',
            'https://www.myinstants.com/media/sounds/eu-sou-rica_1.mp3',
            f'Nova assinatura Tier {tier}: {subscriber_name}!',
            f'Obrigado pela assinatura, {subscriber_name}!'
        )
    except Exception as e:
        logger.error(f"Error handling subscription event: {e}")

async def handle_correlation_result(correlation_future, quantity):
    """
    Handle the result of webhook-to-chat correlation (Story 14)
    Enhanced with monitoring (Story 15)
    """
    global bot_instance, webhook_monitor
    try:
        # Wait for correlation to complete
        correlation_result = await correlation_future
        
        if correlation_result and correlation_result.status == "CORRELATED":
            gifter_name = correlation_result.gifter
            logger.info(f"🎯 CORRELATION SUCCESS: {gifter_name} gifted {correlation_result.quantity} subs")
            
            # STORY 15: Track correlation success
            if webhook_monitor:
                correlation_delay = time.time() - correlation_result.timestamp if hasattr(correlation_result, 'timestamp') else 6.0
                webhook_monitor.track_correlation_success(gifter_name, correlation_result.quantity, correlation_delay)
            
            # Award points using the correlated gifter information
            if bot_instance and gifter_name != 'Unknown' and gifter_name != 'Anonymous':
                try:
                    logger.info(f"🎯 Awarding correlated points to {gifter_name} for {correlation_result.quantity} gifted subs")
                    if hasattr(bot_instance, '_handle_gifted_subscriptions'):
                        await bot_instance._handle_gifted_subscriptions(gifter_name, correlation_result.quantity)
                        logger.info(f"✅ Successfully awarded correlated points to {gifter_name}")
                        
                        # STORY 15: Track correlated points awarded
                        if webhook_monitor:
                            points_awarded = correlation_result.quantity * 200
                            webhook_monitor.track_points_awarded(gifter_name, points_awarded, correlation_result.quantity)
                    else:
                        logger.error("❌ Bot instance doesn't have _handle_gifted_subscriptions method")
                except Exception as e:
                    logger.error(f"❌ Failed to award correlated points to {gifter_name}: {e}")
            elif gifter_name == 'Anonymous':
                logger.info(f"ℹ️ Anonymous correlated gifter - no points awarded")
                if webhook_monitor:
                    webhook_monitor.track_anonymous_gift(correlation_result.quantity, "correlated_anonymous")
            else:
                logger.warning(f"⚠️ Correlated gifter {gifter_name} - no points awarded")
        else:
            logger.warning(f"⚠️ CORRELATION FAILED: No chat message correlation found")
            if webhook_monitor:
                webhook_monitor.track_error("CorrelationError", "No chat message correlation found")
            
    except asyncio.TimeoutError:
        logger.warning(f"⏰ CORRELATION TIMEOUT: No matching chat message found within time window")
        # STORY 15: Track correlation timeout
        if webhook_monitor:
            webhook_data = {"event_id": "correlation_timeout", "timestamp": time.time()}
            webhook_monitor.track_correlation_timeout(webhook_data)
    except Exception as e:
        logger.error(f"❌ CORRELATION ERROR: {e}", exc_info=True)
        if webhook_monitor:
            webhook_monitor.track_error("CorrelationError", f"Correlation processing failed: {str(e)}")

async def handle_gift_subscription_event(event_data, headers=None):
    """
    Handle gifted subscription events using robust multi-strategy parser (Story 13)
    Enhanced with comprehensive monitoring (Story 15)
    """
    global bot_instance, webhook_monitor
    start_time = time.time()
    
    try:
        # STORY 15: Track webhook receipt
        if webhook_monitor:
            webhook_monitor.track_webhook_received('channel.subscription.gifts')
        
        # STORY 13: Use robust multi-strategy parser instead of manual extraction
        parser = WebhookPayloadParser()
        
        # Parse gifter information using cascading strategies
        gifter_result = parser.parse_gifter_info(event_data, headers or {})
        gifter_name, gifter_id = gifter_result
        
        # Extract gift quantity using parser
        quantity = parser.extract_gift_quantity(event_data)
        
        logger.info(f"🎁 PARSER RESULT: {gifter_name} (ID: {gifter_id}) gifted {quantity} subs")
        
        # STORY 15: Track parsing results
        if webhook_monitor:
            if gifter_name != "PENDING_CHAT_CORRELATION" and gifter_name != "Unknown":
                # Determine parsing method based on result
                parsing_method = "unknown_method"  # Default fallback
                if gifter_id:
                    parsing_method = "kick_api_standard"
                elif headers and any("gifter" in str(v).lower() for v in headers.values()):
                    parsing_method = "header_fallback"
                else:
                    parsing_method = "nested_data_parser"
                
                webhook_monitor.track_parsing_success(gifter_name, parsing_method)
            elif gifter_name == "PENDING_CHAT_CORRELATION":
                webhook_monitor.track_parsing_failure(event_data, "Empty payload - triggering correlation")
            else:
                webhook_monitor.track_parsing_failure(event_data, "Unknown gifter - parser failed")
        
        # Handle special case for chat correlation fallback (Story 14)
        if gifter_name == "PENDING_CHAT_CORRELATION":
            logger.info("🔗 CORRELATION: Empty payload detected - starting chat correlation")
            global chat_correlator
            
            if chat_correlator:
                try:
                    # Prepare webhook data for correlation
                    webhook_data = {
                        'event_id': f"webhook_{int(time.time())}",
                        'timestamp': time.time(),
                        'payload': event_data,
                        'quantity': quantity,
                        'bot_instance': bot_instance
                    }
                    
                    # Register for correlation - this will await chat message
                    correlation_future = await chat_correlator.register_webhook_event(webhook_data)
                    
                    # Create background task to handle correlation result
                    asyncio.create_task(handle_correlation_result(correlation_future, quantity))
                    
                    # For now, set gifter as Unknown for immediate processing
                    gifter_name = "Unknown"
                    logger.info("🔗 CORRELATION: Webhook registered, awaiting chat message")
                    
                except Exception as e:
                    logger.error(f"❌ CORRELATION: Failed to register webhook: {e}")
                    gifter_name = "Unknown"
            else:
                logger.error("❌ CORRELATION: Chat correlator not available")
                gifter_name = "Unknown"
        
        logger.info(f"🎁 Gifted subscriptions: {gifter_name} gifted {quantity} subs")
        
        # Award points to gifter using existing points system
        if bot_instance and gifter_name != 'Unknown' and gifter_name != 'Anonymous':
            try:
                logger.info(f"🎯 Awarding points to {gifter_name} for {quantity} gifted subs")
                if hasattr(bot_instance, '_handle_gifted_subscriptions'):
                    await bot_instance._handle_gifted_subscriptions(gifter_name, quantity)
                    logger.info(f"✅ Successfully awarded points to {gifter_name}")
                    
                    # STORY 15: Track points awarded (assuming 200 points per gift)
                    if webhook_monitor:
                        points_awarded = quantity * 200  # Standard gift point value
                        webhook_monitor.track_points_awarded(gifter_name, points_awarded, quantity)
                else:
                    logger.error("❌ Bot instance doesn't have _handle_gifted_subscriptions method")
                    if webhook_monitor:
                        webhook_monitor.track_error("PointsProcessingError", "Bot instance missing _handle_gifted_subscriptions method")
            except Exception as e:
                logger.error(f"❌ Failed to award points to {gifter_name}: {e}", exc_info=True)
                if webhook_monitor:
                    webhook_monitor.track_error("PointsProcessingError", f"Failed to award points: {str(e)}")
        elif gifter_name == 'Anonymous':
            logger.info(f"ℹ️ Anonymous gifter - no points awarded")
            # STORY 15: Track anonymous gifts
            if webhook_monitor:
                webhook_monitor.track_anonymous_gift(quantity, "direct_anonymous")
        elif gifter_name == 'Unknown':
            logger.warning(f"⚠️ Unknown gifter - no points awarded (this needs debugging)")
        else:
            logger.warning(f"⚠️ No bot instance available for points processing")
            if webhook_monitor:
                webhook_monitor.track_error("PointsProcessingError", "Bot instance not available")
        
        # Send gift subscription alert
        await send_alert(
            'https://media1.tenor.com/m/1Nr6H8HTWfUAAAAC/jim-chewing.gif',
            'https://www.myinstants.com/media/sounds/aplausos-efetto-de-sonido.mp3',
            f'{gifter_name} presenteou {quantity} assinatura(s)!',
            f'Muito obrigado pela generosidade, {gifter_name}!'
        )
        
        # STORY 15: Track performance metrics
        if webhook_monitor:
            processing_time = time.time() - start_time
            webhook_monitor.track_performance("webhook_processing", processing_time)
            
    except Exception as e:
        logger.error(f"Error handling gift subscription event: {e}")
        # STORY 15: Track general processing errors
        if webhook_monitor:
            webhook_monitor.track_error("WebhookProcessingError", f"Gift subscription handler failed: {str(e)}")
            processing_time = time.time() - start_time
            webhook_monitor.track_performance("webhook_processing", processing_time)  # Track even failed requests

async def handle_chat_message_event(event_data):
    """Handle chat message events and process bot commands"""
    global bot_instance, processed_messages
    
    try:
        # Extract message information
        message_id = event_data.get('message_id', 'unknown')
        sender_data = event_data.get('sender', {})
        username = sender_data.get('username', 'Unknown')
        content = event_data.get('content', '')
        
        # Deduplication: Check if we've already processed this message recently
        current_time = time.time()
        if message_id in processed_messages:
            time_diff = current_time - processed_messages[message_id]
            if time_diff < DEDUP_WINDOW_SECONDS:
                logger.info(f"🔄 Ignoring duplicate message (ID: {message_id}, {time_diff:.1f}s ago): {username}: {content}")
                return
        
        # Clean old entries from deduplication cache (keep only last hour)
        cutoff_time = current_time - 3600  # 1 hour
        processed_messages = {msg_id: timestamp for msg_id, timestamp in processed_messages.items() if timestamp > cutoff_time}
        
        # Mark this message as processed
        processed_messages[message_id] = current_time
        
        logger.info(f"💬 Chat: {username}: {content}")
        
        # STORY 12: Track gift correlation patterns  
        if username == "Kicklet" and "gifted" in content.lower() and "thank you" in content.lower():
            await track_gift_correlation_message(content, sender_data, event_data)
            
            # STORY 14: Process chat message through correlator
            global chat_correlator
            if chat_correlator:
                try:
                    # Create message object for correlator
                    message_obj = type('Message', (), {
                        'sender': type('Sender', (), {'username': username})(),
                        'content': content,
                        'timestamp': current_time
                    })()
                    
                    # Process through correlator
                    await chat_correlator.process_chat_message(message_obj)
                    logger.info(f"🔗 CORRELATOR: Processed Kicklet message: {content}")
                    
                except Exception as e:
                    logger.error(f"❌ CORRELATOR: Error processing chat message: {e}", exc_info=True)
        
        # If we have a bot instance, process the message for commands
        if bot_instance:
            try:
                # Create a KickMessage-like object from the webhook data
                # This mimics the structure that the bot expects
                message_data = {
                    'id': event_data.get('message_id', 'webhook-msg'),
                    'chatroom_id': getattr(bot_instance, 'chatroom_id', 1164726),
                    'content': content,
                    'type': 'message',
                    'created_at': event_data.get('created_at', ''),
                    'sender': {
                        'id': sender_data.get('user_id', 0),
                        'username': username,
                        'slug': sender_data.get('channel_slug', username.lower()),
                        'identity': sender_data.get('identity', {})
                    }
                }
                
                # Create KickMessage instance
                kick_message = KickMessage(message_data)
                
                # Process the message through the bot's handlers
                await process_bot_message(kick_message)
                
            except Exception as e:
                logger.error(f"Error processing chat message through bot: {e}")
        
    except Exception as e:
        logger.error(f"Error handling chat message event: {e}")

async def process_bot_message(message: KickMessage):
    """Process a chat message through the bot's command and message handlers"""
    global bot_instance
    
    if not bot_instance:
        return
    
    try:
        # Check for command handlers
        content = message.content.strip()
        if content.startswith('!'):
            command = content.split()[0].lower()
            
            # Check if we have a handler for this command
            if hasattr(bot_instance, 'handled_commands') and command in bot_instance.handled_commands:
                handler = bot_instance.handled_commands[command]
                logger.info(f"🤖 Executing command handler for: {command}")
                
                # Execute the command handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(bot_instance, message)
                else:
                    handler(bot_instance, message)
                    
                logger.info(f"✅ Command {command} executed successfully")
            else:
                logger.warning(f"❌ No handler found for command: {command}")
                if hasattr(bot_instance, 'handled_commands'):
                    logger.info(f"📋 Available commands: {list(bot_instance.handled_commands.keys())}")
        
        # Check for message handlers (pattern matching)
        if hasattr(bot_instance, 'handled_messages'):
            for pattern, handler in bot_instance.handled_messages.items():
                if pattern.lower() in content.lower():
                    logger.info(f"🔍 Executing message handler for pattern: {pattern}")
                    
                    if asyncio.iscoroutinefunction(handler):
                        await handler(bot_instance, message)
                    else:
                        handler(bot_instance, message)
                    break  # Only execute first matching handler
                    
    except Exception as e:
        logger.error(f"Error processing bot message: {e}")

def set_bot_instance(bot):
    """Set the bot instance for command processing"""
    global bot_instance
    bot_instance = bot
    logger.info("Bot instance set for webhook command processing")

# STORY 12: Webhook Investigation Functions
# STORY 13: Robust Webhook Payload Parser
# STORY 14: Chat Message Correlation System

class CorrelationResult:
    """Result object for webhook-chat correlation"""
    def __init__(self, gifter, quantity, status="CORRELATED", is_anonymous=False):
        self.gifter = gifter
        self.quantity = quantity
        self.status = status
        self.is_anonymous = is_anonymous
        self.timestamp = time.time()

class WebhookChatCorrelator:
    """
    Correlates empty webhook events with subsequent Kicklet chat messages.
    
    Based on Story 12 investigation findings:
    - Webhook timestamp: 2025-07-29T14:41:11.964Z
    - Chat timestamp: 2025-07-29T14:41:17.743Z
    - Consistent ~6 second delay between webhook and chat message
    - Chat format: "Thank you, USERNAME, for the gifted N subscriptions."
    """
    
    def __init__(self, correlation_timeout=10):
        """
        Initialize correlator with timing window.
        
        Args:
            correlation_timeout (int): Maximum seconds to wait for chat correlation
        """
        self.pending_webhooks = {}  # event_id -> correlation_data
        self.correlation_timeout = correlation_timeout
        self.logger = logging.getLogger(__name__)
        self._cleanup_task = None
        
        # Cleanup task will be started on first webhook registration
    
    async def register_webhook_event(self, webhook_data):
        """
        Register a webhook event for correlation with future chat messages.
        
        Args:
            webhook_data (dict): Webhook event data with event_id, timestamp, payload
            
        Returns:
            asyncio.Future: Future that resolves when correlation completes
        """
        # Start cleanup task if not already running
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_correlations())
        
        event_id = webhook_data.get('event_id', f"webhook_{int(time.time())}")
        timestamp = webhook_data.get('timestamp', time.time())
        
        # Create correlation tracking data
        correlation_data = {
            'event_id': event_id,
            'timestamp': timestamp,
            'webhook_data': webhook_data,
            'status': 'PENDING',
            'future': asyncio.Future()
        }
        
        self.pending_webhooks[event_id] = correlation_data
        self.logger.info(f"🔗 CORRELATOR: Registered webhook {event_id} for correlation")
        
        # Set timeout for correlation
        asyncio.create_task(self._handle_correlation_timeout(event_id))
        
        return correlation_data['future']
    
    async def process_chat_message(self, message):
        """
        Process chat message and attempt correlation with pending webhooks.
        
        Args:
            message: Chat message object with sender and content
        """
        if not self._is_gift_thank_you_message(message):
            return
        
        # Extract gift information from message
        try:
            gifter, quantity = self._extract_gift_info(message)
            message_timestamp = getattr(message, 'timestamp', time.time())
            
            self.logger.info(f"🔗 CORRELATOR: Gift message detected - {gifter} gifted {quantity}")
            
            # Find matching webhook based on timing
            matching_webhook = await self._match_to_pending_webhook(gifter, quantity, message_timestamp)
            
            if matching_webhook:
                # Complete the correlation
                result = CorrelationResult(
                    gifter=gifter,
                    quantity=quantity,
                    is_anonymous=(gifter == "Anonymous")
                )
                
                # Resolve the future
                correlation_data = self.pending_webhooks[matching_webhook]
                if not correlation_data['future'].done():
                    correlation_data['future'].set_result(result)
                
                # Clean up
                del self.pending_webhooks[matching_webhook]
                
                self.logger.info(f"✅ CORRELATOR: Successfully correlated {matching_webhook} with {gifter}")
                
        except Exception as e:
            self.logger.error(f"❌ CORRELATOR: Error processing chat message: {e}", exc_info=True)
    
    def _is_gift_thank_you_message(self, message):
        """
        Check if message is a Kicklet gift thank you message.
        
        Args:
            message: Message object with sender and content
            
        Returns:
            bool: True if this is a gift thank you message
        """
        try:
            if not message or not hasattr(message, 'sender') or not message.sender:
                return False
                
            if not hasattr(message.sender, 'username') or message.sender.username != "Kicklet":
                return False
                
            if not hasattr(message, 'content') or not message.content:
                return False
            
            content = message.content.lower()
            return (
                "thank you" in content and 
                "gifted" in content and 
                "subscription" in content
            )
            
        except Exception as e:
            self.logger.debug(f"🔗 CORRELATOR: Error checking gift message: {e}")
            return False
    
    def _extract_gift_info(self, message):
        """
        Extract gifter name and quantity from Kicklet message.
        
        Args:
            message: Kicklet message object
            
        Returns:
            tuple: (gifter_name, quantity)
        """
        import re
        
        content = message.content
        
        # Pattern: "Thank you, USERNAME, for the gifted N subscriptions."
        pattern = r"Thank you, ([^,]+), for the gifted (\d+) subscriptions?"
        match = re.search(pattern, content)
        
        if match:
            gifter_name = match.group(1).strip()
            quantity = int(match.group(2))
            return gifter_name, quantity
        
        # Fallback: try to extract any username and number
        fallback_pattern = r"([a-zA-Z0-9_]+).*?(\d+)"
        fallback_match = re.search(fallback_pattern, content)
        
        if fallback_match:
            self.logger.warning(f"🔗 CORRELATOR: Using fallback pattern for: {content}")
            return fallback_match.group(1), int(fallback_match.group(2))
        
        return "Unknown", 1
    
    async def _match_to_pending_webhook(self, gifter, quantity, message_timestamp):
        """
        Find the best matching webhook for this chat message.
        
        Args:
            gifter (str): Gifter username from chat
            quantity (int): Number of gifts
            message_timestamp (float): Chat message timestamp
            
        Returns:
            str: Event ID of matching webhook, or None
        """
        best_match = None
        best_score = float('inf')
        
        for event_id, correlation_data in self.pending_webhooks.items():
            webhook_timestamp = correlation_data['timestamp']
            time_diff = abs(message_timestamp - webhook_timestamp)
            
            # Check timing window (5-10 seconds based on Story 12 findings)
            if 4.0 <= time_diff <= 12.0:  # Generous window for reliability
                # Score based on timing (closer = better)
                score = time_diff
                
                if score < best_score:
                    best_score = score
                    best_match = event_id
        
        if best_match:
            self.logger.info(f"🔗 CORRELATOR: Matched {gifter} to webhook {best_match} (timing: {best_score:.1f}s)")
        else:
            self.logger.warning(f"🔗 CORRELATOR: No matching webhook for {gifter} (checked {len(self.pending_webhooks)} pending)")
        
        return best_match
    
    async def _handle_correlation_timeout(self, event_id):
        """
        Handle timeout for webhook correlation.
        
        Args:
            event_id (str): Event ID to timeout
        """
        await asyncio.sleep(self.correlation_timeout)
        
        if event_id in self.pending_webhooks:
            correlation_data = self.pending_webhooks[event_id]
            
            if not correlation_data['future'].done():
                # Set timeout result
                timeout_result = CorrelationResult("TIMEOUT", 0, "TIMEOUT")
                correlation_data['future'].set_result(timeout_result)
            
            # Clean up
            del self.pending_webhooks[event_id]
            self.logger.warning(f"⏰ CORRELATOR: Webhook {event_id} timed out after {self.correlation_timeout}s")
    
    async def _cleanup_expired_correlations(self):
        """Periodic cleanup of expired correlation data"""
        while True:
            try:
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                
                current_time = time.time()
                expired_events = []
                
                for event_id, correlation_data in self.pending_webhooks.items():
                    age = current_time - correlation_data['timestamp']
                    if age > (self.correlation_timeout * 2):  # Double timeout = expired
                        expired_events.append(event_id)
                
                # Clean up expired events
                for event_id in expired_events:
                    if event_id in self.pending_webhooks:
                        del self.pending_webhooks[event_id]
                        self.logger.debug(f"🧹 CORRELATOR: Cleaned up expired event {event_id}")
                
            except Exception as e:
                self.logger.error(f"❌ CORRELATOR: Cleanup error: {e}", exc_info=True)

class WebhookPayloadParser:
    """
    Multi-strategy webhook payload parser for robust gifter information extraction.
    
    Implements cascading parsing strategies to handle various payload formats:
    1. Kick API standard format (direct gifter field)
    2. Nested data structure format  
    3. Flat structure format
    4. Header fallback extraction
    5. Chat correlation fallback
    
    Based on Story 12 investigation findings that confirmed Kick sends empty 
    payloads ({}) for channel.subscription.gifts events.
    """
    
    def __init__(self):
        """Initialize parser with ordered list of parsing strategies"""
        self.parsers = [
            self._parse_kick_api_standard,
            self._parse_nested_data,
            self._parse_flat_structure,
            self._parse_header_fallback
        ]
        self.logger = logging.getLogger(__name__)
    
    def parse_gifter_info(self, payload, headers=None):
        """
        Parse gifter information using cascading strategy approach.
        
        Args:
            payload (dict): Webhook JSON payload
            headers (dict): HTTP request headers
            
        Returns:
            tuple: (username, user_id) or ("PENDING_CHAT_CORRELATION", None) for fallback
        """
        if headers is None:
            headers = {}
        
        self.logger.debug(f"🔍 PARSER: Starting multi-strategy parsing for payload: {payload}")
        
        # Try each parsing strategy in priority order
        for i, parser in enumerate(self.parsers):
            try:
                self.logger.debug(f"🔍 PARSER: Trying strategy {i+1}: {parser.__name__}")
                result = parser(payload, headers)
                
                if result and result[0] and result[0] != "Unknown":
                    self.logger.info(f"✅ PARSER: Success with {parser.__name__} -> {result}")
                    return result
                else:
                    self.logger.debug(f"🔍 PARSER: Strategy {parser.__name__} returned: {result}")
                    
            except Exception as e:
                self.logger.debug(f"🔍 PARSER: Strategy {parser.__name__} failed: {e}")
                continue
        
        # All strategies failed - fallback to chat correlation
        self.logger.info("🔗 PARSER: All strategies failed, triggering chat correlation fallback")
        return ("PENDING_CHAT_CORRELATION", None)
    
    def _parse_kick_api_standard(self, payload, headers):
        """
        Parse standard Kick API format with direct gifter field.
        
        Expected structure:
        {
            "gifter": {
                "username": "user123",
                "user_id": 123456789,
                "is_anonymous": false
            }
        }
        """
        if not isinstance(payload, dict) or 'gifter' not in payload:
            return None
            
        gifter = payload['gifter']
        if not isinstance(gifter, dict):
            return None
        
        # Check for anonymous gifter first
        if gifter.get('is_anonymous', False):
            return ("Anonymous", None)
        
        # Extract username and user_id
        username = gifter.get('username')
        user_id = gifter.get('user_id')
        
        if username:
            return (str(username).strip(), user_id)
        
        return None
    
    def _parse_nested_data(self, payload, headers):
        """
        Parse nested data structure format.
        
        Expected structure:
        {
            "data": {
                "gifter": {
                    "username": "user123",
                    "user_id": 123456789
                }
            }
        }
        """
        if not isinstance(payload, dict) or 'data' not in payload:
            return None
            
        data = payload['data']
        if not isinstance(data, dict) or 'gifter' not in data:
            return None
        
        # Use standard parser on the nested gifter object
        nested_payload = {'gifter': data['gifter']}
        return self._parse_kick_api_standard(nested_payload, headers)
    
    def _parse_flat_structure(self, payload, headers):
        """
        Parse flat structure where gifter fields are at top level.
        
        Expected structure:
        {
            "username": "user123",
            "user_id": 123456789,
            "is_anonymous": false
        }
        """
        if not isinstance(payload, dict):
            return None
        
        # Check for anonymous gifter
        if payload.get('is_anonymous', False):
            return ("Anonymous", None)
        
        # Look for username at top level
        username = payload.get('username') or payload.get('gifter_username')
        user_id = payload.get('user_id') or payload.get('gifter_id')
        
        if username:
            return (str(username).strip(), user_id)
        
        return None
    
    def _parse_header_fallback(self, payload, headers):
        """
        Parse gifter information from HTTP headers as fallback.
        
        Looks for headers like:
        - X-Gifter-Username
        - X-Gifter-ID
        - Kick-Gifter-Info
        """
        if not headers:
            return None
        
        # Look for gifter info in headers
        username = (
            headers.get('X-Gifter-Username') or
            headers.get('Kick-Gifter-Username') or
            headers.get('Gifter-Username')
        )
        
        user_id = (
            headers.get('X-Gifter-ID') or
            headers.get('Kick-Gifter-ID') or
            headers.get('Gifter-ID')
        )
        
        if username:
            try:
                return (str(username).strip(), int(user_id) if user_id else None)
            except (ValueError, TypeError):
                return (str(username).strip(), None)
        
        return None
    
    def extract_gift_quantity(self, payload):
        """
        Extract the number of gifts from payload.
        
        Args:
            payload (dict): Webhook JSON payload
            
        Returns:
            int: Number of gifts/recipients
        """
        if not isinstance(payload, dict):
            return 1  # Default to 1 gift
        
        # Try to get quantity from giftees array
        giftees = payload.get('giftees', [])
        if isinstance(giftees, list) and giftees:
            return len(giftees)
        
        # Try nested data structure
        data = payload.get('data', {})
        if isinstance(data, dict):
            nested_giftees = data.get('giftees', [])
            if isinstance(nested_giftees, list) and nested_giftees:
                return len(nested_giftees)
        
        # Try direct quantity field
        quantity = payload.get('quantity') or payload.get('gift_count')
        if quantity and isinstance(quantity, (int, str)):
            try:
                return max(1, int(quantity))  # Ensure at least 1
            except ValueError:
                pass
        
        # Default to 1 gift
        return 1

async def debug_webhook_request_and_parse(request):
    """
    Log complete webhook request and parse JSON (Story 12)
    Captures all request details and returns parsed JSON
    Returns: (raw_body, parsed_json)
    """
    logger.info("=== WEBHOOK DEBUG START ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Query Parameters: {dict(request.query)}")
    
    # Log raw body and parse JSON
    parsed_json = None
    raw_body = None
    
    try:
        raw_body = await request.read()
        logger.info(f"Raw Body: {raw_body}")
        logger.info(f"Raw Body Length: {len(raw_body)} bytes")
        
        # Try to parse as JSON
        if raw_body:
            try:
                import json
                parsed_json = json.loads(raw_body.decode('utf-8'))
                logger.info(f"Parsed JSON Structure: {json.dumps(parsed_json, indent=2)}")
            except json.JSONDecodeError as e:
                logger.info(f"Body is not valid JSON: {e}")
                parsed_json = None
        else:
            logger.info("Body is empty")
            parsed_json = {}  # Empty payload
            
    except Exception as e:
        logger.error(f"Error reading request body: {e}")
    
    # Log timing information for correlation analysis
    import time
    timestamp = time.time()
    logger.info(f"Request Timestamp: {timestamp}")
    logger.info(f"Request DateTime: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(timestamp))}")
    
    logger.info("=== WEBHOOK DEBUG END ===")
    
    return raw_body, parsed_json

async def document_payload_structure(payload, event_type):
    """
    Document and categorize webhook payload structures (Story 12)
    Helps identify patterns and variations in Kick's webhook payloads
    """
    logger.info("=== PAYLOAD STRUCTURE ANALYSIS START ===")
    logger.info(f"Event Type: {event_type}")
    logger.info(f"Payload Type: {type(payload)}")
    logger.info(f"Payload Keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
    
    # Categorize payload structure
    if not payload or payload == {}:
        logger.info("📋 CATEGORY: Empty payload detected")
        logger.info("📋 ANALYSIS: No data provided - requires correlation with chat messages")
        
    elif isinstance(payload, dict):
        # Check for different structural patterns
        if 'data' in payload:
            logger.info("📋 CATEGORY: Nested data structure detected")
            logger.info(f"📋 ANALYSIS: Data field contains: {list(payload['data'].keys()) if isinstance(payload['data'], dict) else payload['data']}")
            
        elif 'gifter' in payload:
            logger.info("📋 CATEGORY: Standard format detected")
            logger.info(f"📋 ANALYSIS: Direct gifter field with keys: {list(payload['gifter'].keys()) if isinstance(payload['gifter'], dict) else payload['gifter']}")
            
            # Analyze gifter structure
            gifter = payload['gifter']
            if isinstance(gifter, dict):
                is_anonymous = gifter.get('is_anonymous', False)
                has_username = bool(gifter.get('username'))
                has_user_id = bool(gifter.get('user_id'))
                
                logger.info(f"📋 GIFTER ANALYSIS: anonymous={is_anonymous}, has_username={has_username}, has_user_id={has_user_id}")
                
        elif 'giftees' in payload:
            logger.info("📋 CATEGORY: Giftees-only structure detected")
            logger.info(f"📋 ANALYSIS: {len(payload['giftees'])} giftees, no gifter info")
            
        else:
            logger.info("📋 CATEGORY: Unknown structure detected")
            logger.info(f"📋 ANALYSIS: Unexpected keys: {list(payload.keys())}")
    else:
        logger.info(f"📋 CATEGORY: Non-dict payload detected: {type(payload)}")
    
    # Log for correlation tracking
    import time
    correlation_id = f"{event_type}_{int(time.time())}"
    logger.info(f"📋 CORRELATION_ID: {correlation_id}")
    
    logger.info("=== PAYLOAD STRUCTURE ANALYSIS END ===")
    
    return correlation_id

async def track_gift_correlation_message(content, sender_data, event_data):
    """
    Track gift correlation patterns for analysis (Story 12)
    Links Kicklet messages to webhook events for correlation understanding
    """
    logger.info("=== GIFT CORRELATION TRACKING START ===")
    
    # Extract gift information from Kicklet message
    import re
    import time
    
    # Pattern: "Thank you, USERNAME, for the gifted N subscriptions."
    pattern = r"Thank you, ([^,]+), for the gifted (\d+) subscriptions?"
    match = re.search(pattern, content)
    
    if match:
        gifter_name = match.group(1).strip()
        quantity = int(match.group(2))
        
        logger.info(f"🔗 CORRELATION: Extracted gifter='{gifter_name}', quantity={quantity}")
        logger.info(f"🔗 TIMING: Chat message timestamp={time.time()}")
        logger.info(f"🔗 SENDER: {sender_data}")
        logger.info(f"🔗 MESSAGE_DATA: {event_data}")
        
        # Log for correlation analysis
        correlation_data = {
            "type": "chat_gift_message",
            "gifter": gifter_name,
            "quantity": quantity,
            "timestamp": time.time(),
            "full_content": content,
            "sender_data": sender_data
        }
        logger.info(f"🔗 CORRELATION_DATA: {json.dumps(correlation_data, indent=2)}")
        
    else:
        logger.warning(f"🔗 CORRELATION: Failed to parse gift message: {content}")
    
    logger.info("=== GIFT CORRELATION TRACKING END ===")

async def handle_oauth_callback(request):
    """Handle the OAuth callback from Kick"""
    global auth_manager
    
    logger.info(f"Received OAuth callback: {request.url}")
    
    # Extract code from query parameters
    params = request.rel_url.query
    if 'code' in params:
        auth_code = params['code']
        state = params.get('state', 'N/A')
        
        logger.info(f"Received authorization code: {auth_code[:20]}...")
        logger.info(f"State: {state}")
        
        # We need the code_verifier that was used to generate the authorization URL
        # For now, let's try to get it from a temporary file or regenerate the auth flow
        try:
            # Check if we have a stored code_verifier
            verifier_file = Path('oauth_verifier.txt')
            if verifier_file.exists():
                with open(verifier_file, 'r') as f:
                    code_verifier = f.read().strip()
                logger.info("Using stored code verifier")
            else:
                # Generate a new auth flow to get the verifier
                logger.warning("No stored code verifier found. This might cause issues.")
                # For now, let's store the code and let the user complete the process manually
                with open('oauth_code.txt', 'w') as f:
                    f.write(auth_code)
                logger.info(f"Stored authorization code to oauth_code.txt: {auth_code}")
                
                return web.Response(
                    text=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Code Received</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
        .info {{ color: #0066cc; font-size: 18px; }}
        .code {{ background: #f0f0f0; padding: 10px; margin: 20px; font-family: monospace; }}
    </style>
</head>
<body>
    <h1 class="info">✅ Authorization Code Received</h1>
    <p>Your authorization code has been received and stored.</p>
    <div class="code">Code: {auth_code}</div>
    <p>Please run the manual token exchange process.</p>
</body>
</html>
                    """,
                    content_type='text/html'
                )
            
            # Exchange code for tokens
            logger.info("Exchanging authorization code for tokens...")
            tokens = await auth_manager.exchange_code_for_tokens(auth_code, code_verifier)
            logger.info("✅ Tokens received and stored successfully!")
            
            # Clean up temporary files
            try:
                verifier_file.unlink(missing_ok=True)
                Path('oauth_code.txt').unlink(missing_ok=True)
            except:
                pass
            
            return web.Response(
                text="""
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Successful</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
        .success { color: green; font-size: 18px; }
        .info { color: #666; margin-top: 20px; }
    </style>
</head>
<body>
    <h1 class="success">✅ Authorization Successful!</h1>
    <p>Your KickBot has been successfully authorized with OAuth tokens.</p>
    <p class="info">You can now close this window and start your bot.</p>
</body>
</html>
                """,
                content_type='text/html'
            )
            
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return web.Response(
                text=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
        .error {{ color: red; font-size: 18px; }}
        .info {{ color: #666; margin-top: 20px; }}
        .code {{ background: #f0f0f0; padding: 10px; margin: 20px; font-family: monospace; }}
    </style>
</head>
<body>
    <h1 class="error">❌ Authorization Failed</h1>
    <p>Error: {e}</p>
    <div class="code">Code received: {auth_code}</div>
    <p class="info">The code has been stored. Please check the server logs and try manual token exchange.</p>
</body>
</html>
                """,
                content_type='text/html',
                status=500
            )
    else:
        error = params.get('error', 'Unknown error')
        error_description = params.get('error_description', 'No description provided')
        logger.error(f"Authorization failed: {error} - {error_description}")
        
        return web.Response(
            text=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
        .error {{ color: red; font-size: 18px; }}
    </style>
</head>
<body>
    <h1 class="error">❌ Authorization Failed</h1>
    <p>Error: {error}</p>
    <p>Description: {error_description}</p>
</body>
</html>
            """,
            content_type='text/html',
            status=400
        )

async def handle_health(request):
    """Simple health check endpoint"""
    health_data = {
        "status": "ok",
        "service": "Sr_Botoshi Webhook Server",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "oauth": "/callback",
            "events": "/events", 
            "health": "/health"
        }
    }
    return web.json_response(health_data, status=200)

async def handle_kick_events(request):
    """Handle Kick API webhook events with signature verification"""
    global signature_verifier, enable_signature_verification
    
    logger.info(f"Received Kick event webhook: {request.url}")
    
    try:
        # Get the request body
        body = await request.read()
        
        # Signature verification if enabled
        if enable_signature_verification and signature_verifier:
            signature_header = request.headers.get('X-Kick-Signature')
            if not signature_header:
                logger.warning("Missing signature header for webhook verification")
                return web.Response(status=401, text="Missing signature")
            
            # Verify the signature
            is_valid = await signature_verifier.verify_signature(body, signature_header)
            if not is_valid:
                logger.error("Invalid webhook signature")
                return web.Response(status=401, text="Invalid signature")
            
            logger.info("Webhook signature verified successfully")
        
        # STORY 12: Comprehensive webhook request logging for investigation
        raw_body, event_data = await debug_webhook_request_and_parse(request)
        
        if event_data is None:
            logger.error(f"Failed to parse webhook JSON from body: {raw_body}")
            return web.Response(status=400, text="Invalid JSON")
        
        # Get event type from Kick-Event-Type header (standard Kick webhook approach)
        event_type = request.headers.get('Kick-Event-Type', 'unknown')
        event_version = request.headers.get('Kick-Event-Version', '1')
        
        logger.info(f"Received Kick event: {event_type} (version: {event_version})")
        
        # STORY 12: Document payload structure for analysis
        await document_payload_structure(event_data, event_type)
        
        # Fallback detection for events without proper headers
        if event_type == 'unknown':
            # Check for direct chat message structure
            if all(key in event_data for key in ['message_id', 'broadcaster', 'sender', 'content']):
                event_type = 'chat.message.sent'
                logger.info(f"✅ Detected chat message from structure: {event_data.get('sender', {}).get('username', 'unknown')} -> {event_data.get('content', '')}")
            # Check for follow structure - real Kick webhooks have 'follower' and 'broadcaster'
            elif 'follower' in event_data and 'broadcaster' in event_data:
                event_type = 'channel.followed'
            # Check for subscription structure
            elif 'subscriber' in event_data and ('subscribed_at' in event_data or 'gifted_subscriptions' in event_data):
                if 'gifted_subscriptions' in event_data:
                    event_type = 'channel.subscription.gifts'
                else:
                    event_type = 'channel.subscription.new'
        
        # Dispatch events to appropriate handlers
        try:
            if event_type == 'channel.followed':
                # PRODUCTION FIX: Pass full event_data since real webhooks don't have 'data' wrapper
                await handle_follow_event(event_data)
            elif event_type == 'channel.subscription.new':
                # PRODUCTION FIX: Pass full event_data since real webhooks don't have 'data' wrapper
                await handle_subscription_event(event_data)
            elif event_type == 'channel.subscription.gifts':
                # STORY 13: Pass full event_data and headers to robust parser
                # Don't extract 'data' field since Story 12 showed payloads are often empty
                await handle_gift_subscription_event(event_data, dict(request.headers))
            elif event_type == 'channel.subscription.renewal':
                # PRODUCTION FIX: Pass full event_data since real webhooks don't have 'data' wrapper
                await handle_subscription_event(event_data)
            elif event_type == 'chat.message.sent':
                # Process chat messages and execute bot commands
                # For direct message payload structure, pass the entire event_data
                await handle_chat_message_event(event_data)
            else:
                logger.warning(f"Unhandled event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}")
        
        return web.Response(status=200, text="Event received")
        
    except Exception as e:
        logger.error(f"Error handling Kick event: {e}")
        return web.Response(status=500, text="Internal server error")

async def create_app() -> web.Application:
    """Create and configure the webhook application"""
    global auth_manager, signature_verifier, chat_correlator, webhook_monitor, webhook_diagnostics, enable_signature_verification
    
    # Initialize chat correlator for Story 14
    try:
        chat_correlator = WebhookChatCorrelator()
        logger.info("WebhookChatCorrelator initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WebhookChatCorrelator: {e}")
    
    # Initialize monitoring system for Story 15
    try:
        webhook_monitor = WebhookMonitoring()
        webhook_diagnostics = WebhookDiagnostics()
        webhook_diagnostics.set_monitor(webhook_monitor)
        logger.info("WebhookMonitoring and WebhookDiagnostics initialized")
    except Exception as e:
        logger.error(f"Failed to initialize monitoring system: {e}")
    
    # Initialize auth manager
    try:
        auth_manager = KickAuthManager()
        logger.info("KickAuthManager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize KickAuthManager: {e}")
        # Don't return here, allow app to start without auth manager for basic functionality
    
    # Initialize signature verifier if enabled
    if enable_signature_verification:
        try:
            signature_verifier = KickSignatureVerifier()
            logger.info("KickSignatureVerifier initialized")
        except Exception as e:
            logger.error(f"Failed to initialize KickSignatureVerifier: {e}")
            enable_signature_verification = False
    
    # Create web application
    app = web.Application()
    app.router.add_get('/callback', handle_oauth_callback)
    app.router.add_post('/events', handle_kick_events)  # Kick API events
    app.router.add_get('/health', handle_health)
    app.router.add_get('/', handle_health)  # Root endpoint for basic health check
    
    # Add diagnostic endpoint for Story 15
    if webhook_diagnostics:
        app.router.add_get('/diagnostics/webhooks', webhook_diagnostics.handle_diagnostics_request)
    
    return app

async def main():
    """Main function to start the unified webhook server"""
    global enable_signature_verification
    
    # Read signature verification setting from environment or settings
    enable_signature_verification = os.environ.get('KICK_WEBHOOK_SIGNATURE_VERIFICATION', 'false').lower() == 'true'
    if enable_signature_verification:
        logger.info("Webhook signature verification is ENABLED")
    else:
        logger.info("Webhook signature verification is DISABLED")
    
    # Create the application
    app = await create_app()
    
    # Start the server on port 8080 (unified port for both OAuth and webhooks)
    port = int(os.environ.get('KICK_WEBHOOK_PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🚀 Unified Webhook Server started on port {port}")
    logger.info(f"📋 Available endpoints:")
    logger.info(f"  - OAuth Callback: http://0.0.0.0:{port}/callback")
    logger.info(f"  - Webhook Events: http://0.0.0.0:{port}/events")
    logger.info(f"  - Health Check: http://0.0.0.0:{port}/health")
    logger.info(f"🌐 External URL (via nginx): https://webhook.botoshi.sats4.life/")
    logger.info("✅ Server is ready to receive OAuth callbacks and webhook events...")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour at a time
    except KeyboardInterrupt:
        logger.info("Shutting down unified webhook server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())