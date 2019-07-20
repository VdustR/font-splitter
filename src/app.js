const { spawnSync, execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const chunk = require('lodash/chunk');
const template = require('lodash/template');
const mkdirp = require('mkdirp');
const slugify = require('slugify');
/**
 * replace this with String.prototype.matchAll after node 12.0.0
 */
const matchAll = require('string.prototype.matchall');

const ttx = (fontPath, table) => {
  const { stdout } = spawnSync('ttx', ['-t', table, '-o', '-', fontPath], {
    encoding: 'utf8',
  });
  return stdout;
};

const getFontName = fontPath => {
  const name = ttx(fontPath, 'name');
  const data = Object.assign(
    {},
    ...[
      ...matchAll(
        name,
        /<namerecord (?:[^>]+ )?nameID="(1|2|4|6)"(?: [^>]+)>[\n\s]*([^<\n]+)[\n\s]*<\/namerecord>/g
      ),
    ].map(([, id, value]) => ({ [id]: value }))
  );
  const fontNameOrigin = data[1];
  const fontWeight = data[2];
  const fontFullName = data[4];
  const fileName = data[6];
  const fontFamily =
    fontNameOrigin.substr(0 - fontWeight.length) === fontWeight
      ? fontNameOrigin
          .substring(0, fontNameOrigin.length - fontWeight.length)
          .trim()
      : fontNameOrigin;
  const locals = [fontFullName, fileName];
  return { fontFamily, locals };
};

const uniqueArr = arr => [...new Set(arr)];

const hexToInt = str => parseInt(str, 16);
const intToHex = num => num.toString(16);

const getAllCodes = fontPath => {
  const cmap = ttx(fontPath, 'cmap');
  const matches = [...matchAll(cmap, /<map code="0x([^"]+)" name="/g)];
  const codes = uniqueArr(matches.map(match => hexToInt(match[1]))).sort(
    (a, b) => a - b
  );
  return codes;
};

const getAllCodeBlocks = () => {
  const content = fs.readFileSync(path.join(__dirname, 'unicodeBlocks'), {
    encoding: 'utf8',
  });
  const lines = content.split('\n');
  const blocks = lines
    .filter(a => a)
    .map(line => {
      const [[, start, end, description]] = matchAll(
        line,
        /U\+([^.]+)..U\+([^\t]+)\t(.+)/
      );
      return {
        start: hexToInt(start),
        end: hexToInt(end),
        description,
      };
    });
  return blocks;
};

const getUnicodeRanges = arr => {
  const ranges = [];
  const putNewRange = val => ranges.push([val]);
  const putOldRange = val => ranges[ranges.length - 1].push(val);
  putNewRange(arr[0]);
  for (let i = 1; i < arr.length; i++) {
    if (arr[i] === arr[i - 1] + 1) {
      putOldRange(arr[i]);
    } else {
      putNewRange(arr[i]);
    }
  }
  const unicodeRanges = ranges.map(range =>
    range.length === 1
      ? `U+${intToHex(range[0])}`
      : `U+${intToHex(range[0])}-${intToHex(range[range.length - 1])}`
  );
  return unicodeRanges;
};

const getFontBasename = fontPath => {
  const extName = path.extname(fontPath);
  const basename = path.basename(fontPath, extName);
  return basename;
};

const genSubset = ({ splitTarget, flavor, output, fontPath }) => {
  const { description, codes } = splitTarget;
  const unicodeRanges = getUnicodeRanges(codes);
  const targetFontName = `${getFontBasename(fontPath)}.${slugify(
    description
  )}.${flavor}`;
  execFileSync('pyftsubset', [
    `--unicodes=${unicodeRanges.join(',')}`,
    '--with-zopfli',
    `--flavor=${flavor}`,
    `--output-file=${path.join(output, targetFontName)}`,
    fontPath,
  ]);
  return {
    codes,
    targetFontName,
  };
};

const getSplitTargets = ({ codeBlocks, codes, chunkSize }) => {
  const splitTargets = [];
  codeBlocks.forEach(codeBlock => {
    const { start, end, description } = codeBlock;
    const currentCodes = codes.filter(code => code >= start && code <= end);
    if (currentCodes.length === 0) {
      return;
    }
    if (currentCodes.length > chunkSize) {
      const newCodeRanges = chunk(currentCodes, chunkSize);
      const countLength = String(newCodeRanges.length).length;
      splitTargets.push(
        ...newCodeRanges.map((newCodeRange, i) => ({
          description: `${description} ${String(i + 1).padStart(
            countLength,
            '0'
          )}`,
          codes: newCodeRange,
        }))
      );
    } else {
      splitTargets.push({
        description: description,
        codes: currentCodes,
      });
    }
  });
  return splitTargets;
};

const genCss = ({
  fontFamily,
  locals,
  results,
  style,
  weight,
  output,
  fontPath,
}) => {
  const banner = fs.readFileSync(path.join(__dirname, 'banner.css'), {
    encoding: 'utf8',
  });
  const cssTemplate = fs.readFileSync(path.join(__dirname, 'font.css'), {
    encoding: 'utf8',
  });
  const compiled = template(cssTemplate);
  const css = results
    .map(result =>
      compiled({
        fontFamily,
        fontStyle: style,
        fontWeight: weight,
        src: [
          ...locals.map(local => `local('${local}')`),
          `url(${result.targetFontName})`,
        ].join(', '),
        unicodeRange: getUnicodeRanges(result.codes).join(', '),
      })
    )
    .join('\n');
  const basename = getFontBasename(fontPath);
  fs.writeFileSync(
    path.resolve(output, `${basename}.css`),
    `${[banner, css].join('\n')}`
  );
};

const genSubsets = ({
  flavor,
  output,
  fontPath,
  chunkSize,
  family,
  style,
  weight,
  dryRun,
  quite,
}) => {
  const log = (...args) => {
    if (quite) return;
    console.log(...args);
  };
  const codeBlocks = getAllCodeBlocks();
  log('Calculating...');
  let { fontFamily, locals } = getFontName(fontPath);
  if (family) fontFamily = family;
  log(`Font Family: ${fontFamily}`);
  log(`Locals: ${locals.join(', ')}`);
  const codes = getAllCodes(fontPath);
  const splitTargets = getSplitTargets({ codeBlocks, codes, chunkSize });
  splitTargets.forEach(splitTarget =>
    log(`${splitTarget.description}: ${splitTarget.codes.length}`)
  );
  log(`Split total: ${splitTargets.length}`);
  if (dryRun) {
    return;
  }
  mkdirp.sync(output);
  log('Fonts generating...');
  const results = splitTargets.map((splitTarget, i) => {
    const result = genSubset({ splitTarget, flavor, output, fontPath });
    log(
      `${String(i + 1).padStart(String(splitTargets.length).length, 0)}/${
        splitTargets.length
      } ${splitTarget.description}`
    );
    return result;
  });
  log('Fonts generated!');
  log('CSS generating...');
  genCss({
    fontFamily,
    locals,
    results,
    style,
    weight,
    output,
    fontPath,
  });
  log('CSS generated!');
  log('Font split success!');
};

module.exports = genSubsets;
