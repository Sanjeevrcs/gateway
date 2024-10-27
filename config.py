# config.py

AUTH_URL_TEMPLATE = 'http://{tenant}.localhost:8000/api/v1/gateway/authenticate/'
SSE_URL_TEMPLATE = 'http://{tenant}.localhost:8000/api/v1/gateway/events/{gateway_id}/'
HEARTBEAT_URL_TEMPLATE = 'http://{tenant}.localhost:8000/api/v1/gateway/{gateway_id}/heartbeat'
