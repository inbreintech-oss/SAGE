FROM node:22-alpine AS builder
WORKDIR /app

ENV NODE_ENV=development
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# Copy project files
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./

COPY packages/app/package.json ./packages/app/package.json
COPY packages/brewsync-datatable/package.json ./packages/brewsync-datatable/package.json

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy sources
COPY . .

# Build datatable
RUN pnpm --filter brewsync-datatable run build

# Build app
RUN pnpm --filter admin-frontend run build

FROM nginx:stable-alpine AS serve

COPY --from=builder /app/packages/app/dist /app/dist
COPY nginx/nginx.conf.template /etc/nginx/templates/default.conf.template

COPY nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "deamon off;"]