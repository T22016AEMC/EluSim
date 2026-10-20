import ts from "../frontend/node_modules/typescript/lib/typescript.js";
import fs from "node:fs";
const values = new Map();
for (const name of fs.readdirSync("frontend/src").filter(name => /\.tsx?$/.test(name))) {
  const text = fs.readFileSync("frontend/src/" + name, "utf8");
  const source = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, true);
  function visit(node) {
    if (ts.isJsxText(node) || ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const value = node.text.replace(/\s+/g, " ").trim();
      if (/[A-Za-z\u4e00-\u9fff]/.test(value)) {
        if (!values.has(value)) values.set(value, []);
        values.get(value).push(name);
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
}
fs.writeFileSync("review/phase2.2/source-strings.json", JSON.stringify(Object.fromEntries(values), null, 2));
console.log([...values.keys()].filter(v => v.includes(" ") || /[\u4e00-\u9fff]/.test(v)).map((v,i) => i+"\t"+v).join("\n"));
