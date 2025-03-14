FROM ubuntu:latest

# Install dependencies
RUN apt-get update && apt-get install -y curl

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set Ollama to listen on all interfaces
ENV OLLAMA_HOST=0.0.0.0:11434

# Expose the Ollama port
EXPOSE 11434

# Start Ollama
CMD ["ollama", "serve"]
