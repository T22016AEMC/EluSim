import ts from "../frontend/node_modules/typescript/lib/typescript.js";
import fs from "node:fs";
const catalog = JSON.parse(fs.readFileSync("backend/elusim/zh_tw.json", "utf8"));
const machine = new Set(["RP","NP","HILIC","IEX","SEC","small_molecule","parameterized","oligomer","polymer","peptide","protein","Water","None","Generic","Generic C18","Experimental model prediction","Experimental","Literature-derived","Insufficient data","Unsupported","Qualitative screening","Screening only","Calibrated","Model-based","Measured","Unknown / Legacy","normalized relative absorption (dimensionless)","molar absorptivity (L mol^-1 cm^-1)"]);
for (const name of fs.readdirSync("frontend/src").filter(name => /\.tsx?$/.test(name) && !["RetentionWorkspace.tsx","project.ts","types.ts","sources.ts"].includes(name))) {
  const path = "frontend/src/" + name;
  let text = fs.readFileSync(path, "utf8");
  const source = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, true);
  const edits = [];
  function visit(node) {
    if (ts.isJsxText(node)) {
      const key = node.text.replace(/\s+/g," ").trim();
      if (catalog[key]) edits.push([node.getStart(source),node.end,"{tr("+JSON.stringify(key)+")}"]);
    } else if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const key = node.text.replace(/\s+/g," ").trim();
      if (catalog[key] && !machine.has(key) && !(ts.isPropertyAssignment(node.parent) && node.parent.name===node)) {
        const expression = "tr(" + JSON.stringify(key) + ")";
        const prefix = node.text.match(/^\s+/)?.[0] ?? "";
        const suffix = node.text.match(/\s+$/)?.[0] ?? "";
        const rendered = prefix || suffix ? "(" + [prefix && JSON.stringify(prefix),expression,suffix && JSON.stringify(suffix)].filter(Boolean).join(" + ") + ")" : expression;
        edits.push([node.getStart(source),node.end,ts.isJsxAttribute(node.parent) ? "{"+rendered+"}" : rendered]);
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  for (const [start,end,value] of edits.sort((a,b)=>b[0]-a[0])) text=text.slice(0,start)+value+text.slice(end);
  if (edits.length || text.includes('t("empty_compounds")') || text.includes('t("report0259_info")')) {
    text=text.replaceAll('t("empty_compounds")','tr("empty_compounds")').replaceAll('t("report0259_info")','tr("report0259_info")');
    text='import { t as tr } from "./i18n/zh-TW";\n'+text;
  }
  fs.writeFileSync(path,text);
}
