#!/bin/sh
set -e

# 환경변수 치환
envsubst '$BREWSYNC_CLIENT_PORT $BREWSYNC_API_ENDPOINT $BREWSYNC_API_URL' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Nginx 실행
exec nginx -g 'daemon off;'
