FROM nodered/node-red:latest

RUN npm install \
    @flowfuse/node-red-dashboard \
    node-red-contrib-telegrambot \
    node-red-contrib-tfjs-coco-ssd \
    node-red-node-sqlite \
    --no-audit --no-fund && \
    npm cache clean --force

ENV TZ=America/Santiago
