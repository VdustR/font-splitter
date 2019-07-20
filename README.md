# Font Splitter

![npm](https://img.shields.io/npm/v/font-splitter.svg)

Split the big font file into small subsets.

Font Splitter will split the font and generate a css with [`unicode-range`](https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face/unicode-range) just like Google fonts do.

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
$ font-splitter
Usage: font-splitter [options] <fontPath>

Options:
  -v, --version          output the version number
  -c, --chunk <chunk>    chunk size, `-` stand for infinity, default: 256
  -f, --flavor <flavor>  font flavor: otf, ttf, woff, woff2
  -n, --family <family>  font family, default: parsed from font
  -s, --style <style>    font style, default: normal
  -w, --weight <weight>  font weight, default: 400
  -d, --dry              dry run
  -q, --quite            disable stdout
  -o, --output <output>  output directory
  -h, --help             output usage information
```

## Docker

```sh
docker run --rm -it -v </path/to/your/font>:/fonts vdustr/font-splitter <font.woff2>
```

### Build Your Image

```sh
docker build -t vdustr/font-splitter .
```
