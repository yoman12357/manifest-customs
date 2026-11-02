FROM ollama/ollama:0.12.6
COPY deploy/vision-start.sh /vision-start.sh
ENV OLLAMA_HOST=0.0.0.0:11434
EXPOSE 11434
ENTRYPOINT ["/bin/sh", "/vision-start.sh"]
