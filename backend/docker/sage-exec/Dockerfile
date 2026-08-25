FROM python:3.11-slim-bookworm

RUN useradd -m -u 10001 -s /bin/bash sageexec

WORKDIR /opt/sage-exec

COPY docker/sage-exec/requirements-exec.txt .
RUN pip install --no-cache-dir -r requirements-exec.txt && chown -R sageexec:sageexec /opt/sage-exec

USER sageexec

# sage/ 코드는 이미지에 bake 하지 않음 — /host/n2 bind mount 가 유일한 소스
ENV PYTHONPATH=/host/n2
ENV SAGE_EXEC_MODE=daemon
ENV SAGE_EXEC_DAEMON_PORT=9000
ENV NARRATIX_HOME=/host/n2

EXPOSE 9000
CMD ["python", "-m", "sage.exec.daemon"]
