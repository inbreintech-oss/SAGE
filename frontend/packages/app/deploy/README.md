# Admin-Frontend Deployment

## Deploy Environments

BrewSync/admin-frontend 프로젝트는 두 가지 환경에서 배포될 수 있습니다
- dev: vite dev를 그대로 실행시키는 개발 환경, 디버깅 가능
- prod: 정적 파일로 serve 된 프로덕션 환경, nginx로 서빙됨.

## How to Build and Run

```
# project root에서 실행해야 합니다.
cd ..

# dev 환경 빌드
docker build -t admin-frontend:dev -f .\deploy\dev\Dockerfile .
docker build -t admin-frontend:prod -f .\deploy\prod\Dockerfile .

# dev 환경 실행
docker run -itd --name admin-frontend-dev -p 5000:5000 --env-file .\.env admin-frontend:dev
docker run -itd --name admin-frontend-prod -p 5000:5000 --env-file .\.env admin-frontend:prod
```

## Environment Variables

> production 빌드에서만 사용되는 환경 변수들입니다. nginx 설정에 사용됩니다.

| Name                  | Description                    |
|-----------------------|--------------------------------|
| BREWSYNC_CLIENT_PORT  | admin-frontend가 listen할 포트     |
| BREWSYNC_API_URL      | api 서버의 url, 예: http://backend |
| BREWSYNC_API_ENDPOINT | api 서버의 endpoint, 예: /api      |
