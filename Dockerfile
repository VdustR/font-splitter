FROM sandinh/fonttools
RUN apk add --no-cache \
  nodejs \
  yarn
WORKDIR /font-splitter
COPY ./package.json .
COPY ./yarn.lock .
RUN yarn --prod
ENV PATH="/font-splitter/bin:${PATH}"
COPY ./bin bin
COPY ./src src
WORKDIR /fonts
ENTRYPOINT [ "font-splitter" ]
