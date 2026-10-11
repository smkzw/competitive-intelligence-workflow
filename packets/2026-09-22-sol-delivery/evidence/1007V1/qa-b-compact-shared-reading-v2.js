// Fresh candidate, same real task; include the pixel-rejection root causes.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const base = path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-compact-shared-reading-v1.js");
const raw = await fs.readFile(base);
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "1fccc85ba662cf91ba525823c8db79d29f53b89eb2262ed3f2754ce975395d6a")
  throw Error("Previous terminal QA recipe changed");
const checks = `
        const main = document.querySelector('.kz-b-main');
        const module = panel.parentElement;
        const geometry = {alignContent: getComputedStyle(main).alignContent,
          panelWidth: panel.getBoundingClientRect().width,
          moduleWidth: module.getBoundingClientRect().width,
          panels: module.children.length};
        if (geometry.alignContent !== 'start') failures.push('grid rows stretch');
        if (geometry.panels === 1 && geometry.panelWidth < geometry.moduleWidth * .98)
          failures.push('single panel wastes desktop width');
        if (panel.querySelector('h4')?.textContent.includes('Continuous'))
          failures.push('raw continuous label leaked');
        if (option.yAxis[0].name === 'years') failures.push('native axis unit ignored');
        const footer = document.querySelector('#external-sources').innerText;
        if (/SHA-256|当前工作区|不在载荷中虚构/.test(footer))
          failures.push('internal retrieval notes in public footer');
`;
const source = raw.toString().replaceAll('.artifacts/1007-b-compact-shared-reading-v1',
  '.artifacts/1007-b-compact-shared-reading-v2').replace(
    'return {rowCount: rows.length, studyCount, visibleIds, names, legend, glyphs, failures,',
    checks + 'return {rowCount: rows.length, studyCount, visibleIds, names, legend, glyphs,' +
      ' failures, geometry,');
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
