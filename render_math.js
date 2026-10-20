// build-time KaTeX: reads [{e: "latex", d: displayMode}] on stdin, prints a JSON array of HTML strings.
const katex = require("katex");
const items = JSON.parse(require("fs").readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(items.map(i =>
  katex.renderToString(i.e, { displayMode: i.d, throwOnError: false, output: "htmlAndMathml" }))));
