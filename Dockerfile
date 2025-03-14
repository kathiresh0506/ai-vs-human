# Use an official Ubuntu image as a base
FROM ubuntu:22.04

# Install curl to download Ollama
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://ollama.com/install.sh | sh

# Expose Ollama's default API port (11434)
EXPOSE 11434



# Run Ollama's server when the container starts
CMD ["your_app", "--host=0.0.0.0", "--port=11434"]

