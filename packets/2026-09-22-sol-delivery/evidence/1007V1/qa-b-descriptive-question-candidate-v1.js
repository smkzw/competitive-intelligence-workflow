// One bounded parameterized recipe for new immutable descriptive candidates.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
if (!/^\.artifacts\/1007-b-descriptive-question-preview-v\d+$/.test(candidateRelative))
  throw Error("Explicit descriptive candidate path required");
const directory = path.join(workflowRoot,"packets/2026-09-22-sol-delivery/evidence/1007V1");
const raw = await fs.readFile(path.join(directory,"qa-b-descriptive-question-preview-v1.js"));
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "5ed028228ad5faea62b24a525ec6f29f646e81ac3b9503ba0e5e9e0c8e1fc0bf")
  throw Error("Frozen task recipe changed");
await new(Object.getPrototypeOf(async function(){}).constructor)("taskSpace","workflowRoot",
  raw.toString().replaceAll(".artifacts/1007-b-descriptive-question-preview-v1",
    candidateRelative))(taskSpace,workflowRoot);
const paired=await fs.readFile(path.join(directory,"qa-b-question-paired-reading-v2.js"),"utf8");
await new(Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace","workflowRoot","candidateRelative",paired)(taskSpace,workflowRoot,candidateRelative);
