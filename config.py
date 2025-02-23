# config.py
ATTACKBOX_SERVER_DOMAIN = 'localhost:8000'
PROTOCOL = 'http'
KAFKA_URL = '172.210.111.156:9092'


AUTH_URL_TEMPLATE = '{protocol}://{tenant}.{domain}/api/v1/gateway/authenticate/'
SSE_URL_TEMPLATE = '{protocol}://{tenant}.{domain}/api/v1/gateway/events/{gateway_id}/'
HEARTBEAT_URL_TEMPLATE = '{protocol}://{tenant}.{domain}/api/v1/gateway/{gateway_id}/heartbeat'
