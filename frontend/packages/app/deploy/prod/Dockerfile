FROM node:20-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
COPY . /app
WORKDIR /app

FROM base AS build
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
RUN pnpm build

FROM nginx:stable-alpine AS serve

COPY ./deploy/prod/default.conf.template /etc/nginx/templates/default.conf.template
COPY ./deploy/prod/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --from=build /app/dist /app/dist

EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
