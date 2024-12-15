# config.py
ATTACKBOX_SERVER_DOMAIN = 'localhost:8000'
PROTOCOL = 'http'
AUTH_URL_TEMPLATE = '{protocol}://{tenant}.{domain}/api/v1/gateway/authenticate/'
SSE_URL_TEMPLATE = '{protocol}://{tenant}.{domain}/api/v1/gateway/events/{gateway_id}/'
HEARTBEAT_URL_TEMPLATE = '{protocol}://{tenant}.{domain}/api/v1/gateway/{gateway_id}/heartbeat'
KAFKA_URL = 'localhost:9092'
