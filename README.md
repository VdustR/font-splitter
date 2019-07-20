# Font Splitter

Split the big font file into small subsets.

## Requirement

- [Node.js](https://nodejs.org) 10.0.0+
- [FontTools](https://github.com/fonttools/fonttools)

## Installation

```sh
npm i -g font-splitter
yarn global add font-splitter
```

## Usage

```sh
font-splitter [options] <fontPath>
```

Execute for help:

```sh
font-splitter
```

## Docker

```sh
docker run --rm -it -v </path/to/your/font>:/fonts vdustr/font-splitter <font.woff2>
```

### Build Your Image

```sh
docker build -t vdustr/font-splitter .
```
