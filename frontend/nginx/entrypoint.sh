#!/bin/sh
set -e

# 환경변수 기본값 설정
export BREWSYNC_CLIENT_PORT=${BREWSYNC_CLIENT_PORT:-5000}
export BREWSYNC_API_ENDPOINT=${BREWSYNC_API_ENDPOINT:-/api}
export BREWSYNC_API_URL=${BREWSYNC_API_URL:-http://localhost:5555}

echo "Starting nginx with configuration:"
echo "  BREWSYNC_CLIENT_PORT: $BREWSYNC_CLIENT_PORT"
echo "  BREWSYNC_API_ENDPOINT: $BREWSYNC_API_ENDPOINT"
echo "  BREWSYNC_API_URL: $BREWSYNC_API_URL"

# 환경변수 치환
envsubst '$BREWSYNC_CLIENT_PORT $BREWSYNC_API_ENDPOINT $BREWSYNC_API_URL' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Nginx 설정 테스트
nginx -t

# Nginx 실행
exec nginx -g 'daemon off;'
