# --- STAGE 1: The Construction Room (Builder) ---
    FROM alpine:latest AS builder

    # 1. Install only what we need to compile code
    RUN apk add --no-cache \
        git \
        make \
        g++ \
        linux-headers
    
    # 2. Clone the official Stockfish source code from GitHub
    # We use a specific "tag" or "hash" for absolute certainty
    WORKDIR /src
    RUN git clone --depth 1 --branch sf_16.1 https://github.com/official-stockfish/Stockfish.git .
    
    # 3. Compile the code for a standard 64-bit architecture
    WORKDIR /src/src
    RUN make -j profile-build ARCH=x86-64-modern
    
    # --- STAGE 2: The Clean Room (Final Image) ---
    FROM alpine:latest
    
    # Install only the light runtime libraries Stockfish needs to "breathe"
    RUN apk add --no-cache libstdc++ libgcc socat

    # 4. Copy ONLY the finished executable from the builder
    # We leave the compilers and git history behind!
    COPY --from=builder /src/src/stockfish /usr/local/bin/stockfish
    
    # 5. Run as a non-root user (Security Best Practice)
    RUN adduser -D chessuser
    USER chessuser
    
    # ENTRYPOINT ["stockfish"]
    ENTRYPOINT ["sh", "-c", \
        "socat TCP-LISTEN:3334,reuseaddr,fork EXEC:'stockfish',pty,stderr"]