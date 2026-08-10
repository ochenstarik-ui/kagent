import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as ts from "typescript";

const reasoningSource = readFileSync(
  fileURLToPath(new URL("../src/reasoning.ts", import.meta.url)),
  "utf8"
);
const indexSource = readFileSync(
  fileURLToPath(new URL("../src/index.ts", import.meta.url)),
  "utf8"
);
const engineSource = readFileSync(
  fileURLToPath(
    new URL("../../../services/reasoning-engine/src/engine.py", import.meta.url)
  ),
  "utf8"
);
const serverSource = readFileSync(
  fileURLToPath(
    new URL("../../../services/reasoning-engine/src/server.py", import.meta.url)
  ),
  "utf8"
);

function parseTypeScript(source: string, fileName: string): ts.SourceFile {
  return ts.createSourceFile(
    fileName,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS
  );
}

function typeScriptUnionValues(typeName: string): string[] {
  const sourceFile = parseTypeScript(reasoningSource, "reasoning.ts");
  const declaration = sourceFile.statements.find(
    (statement): statement is ts.TypeAliasDeclaration =>
      ts.isTypeAliasDeclaration(statement) && statement.name.text === typeName
  );
  assert.ok(declaration, `Missing TypeScript type alias ${typeName}`);
  assert.ok(
    ts.isUnionTypeNode(declaration.type),
    `TypeScript type ${typeName} must be a string union`
  );

  return declaration.type.types.map((member) => {
    assert.ok(
      ts.isLiteralTypeNode(member) && ts.isStringLiteral(member.literal),
      `TypeScript type ${typeName} contains a non-string member`
    );
    return member.literal.text;
  });
}

function typeScriptInterfaceFields(interfaceName: string): string[] {
  const sourceFile = parseTypeScript(reasoningSource, "reasoning.ts");
  const declaration = sourceFile.statements.find(
    (statement): statement is ts.InterfaceDeclaration =>
      ts.isInterfaceDeclaration(statement) && statement.name.text === interfaceName
  );
  assert.ok(declaration, `Missing TypeScript interface ${interfaceName}`);

  return declaration.members.map((member) => {
    assert.ok(
      ts.isPropertySignature(member) && member.name !== undefined &&
        ts.isIdentifier(member.name),
      `TypeScript interface ${interfaceName} contains an unsupported member`
    );
    return member.name.text;
  });
}

function pythonClassBody(source: string, className: string): string[] {
  const lines = source.split(/\r?\n/u);
  const classPattern = new RegExp(
    `^class ${className}(?:\\([^)]*\\))?:\\s*$`,
    "u"
  );
  const classLine = lines.findIndex((line) => classPattern.test(line));
  assert.notEqual(classLine, -1, `Missing Python class ${className}`);

  const body: string[] = [];
  for (const line of lines.slice(classLine + 1)) {
    if (line.length > 0 && !/^\s/u.test(line)) {
      break;
    }
    body.push(line);
  }
  return body;
}

function pythonEnumValues(enumName: string): string[] {
  return pythonClassBody(engineSource, enumName).flatMap((line) => {
    const match = /^\s+[A-Z][A-Z0-9_]*\s*=\s*"([^"]+)"\s*$/u.exec(line);
    return match?.[1] === undefined ? [] : [match[1]];
  });
}

function snakeToCamel(value: string): string {
  return value.replace(/_([a-z])/gu, (_match, letter: string) =>
    letter.toUpperCase()
  );
}

function pythonRequestFields(): string[] {
  return pythonClassBody(serverSource, "DecideRequest").flatMap((line) => {
    const match = /^\s+([a-z][a-z0-9_]*)\s*:/u.exec(line);
    return match?.[1] === undefined ? [] : [snakeToCamel(match[1])];
  });
}

function assertSameMembers(
  contractName: string,
  typeScriptMembers: string[],
  pythonMembers: string[]
): void {
  const typeScriptSet = new Set(typeScriptMembers);
  const pythonSet = new Set(pythonMembers);
  const onlyInTypeScript = [...typeScriptSet]
    .filter((member) => !pythonSet.has(member))
    .sort();
  const onlyInPython = [...pythonSet]
    .filter((member) => !typeScriptSet.has(member))
    .sort();

  assert.deepEqual(
    { onlyInTypeScript, onlyInPython },
    { onlyInTypeScript: [], onlyInPython: [] },
    `${contractName} differ between TypeScript and Python`
  );
}

test("exports the Reasoning Engine contract from the package entry point", () => {
  const sourceFile = parseTypeScript(indexSource, "index.ts");
  const exports = sourceFile.statements.flatMap((statement) =>
    ts.isExportDeclaration(statement) &&
    statement.moduleSpecifier !== undefined &&
    ts.isStringLiteral(statement.moduleSpecifier)
      ? [statement.moduleSpecifier.text]
      : []
  );

  assert.ok(exports.includes("./reasoning.js"), "Missing ./reasoning.js export");
});

test("keeps ReasoningRequest fields aligned with DecideRequest", () => {
  assertSameMembers(
    "ReasoningRequest fields",
    typeScriptInterfaceFields("ReasoningRequest"),
    pythonRequestFields()
  );
});

for (const enumName of [
  "Capability",
  "PrivacyClass",
  "ExecutionMode",
  "TaskCategory"
]) {
  test(`keeps ${enumName} values aligned with Python`, () => {
    assertSameMembers(
      `${enumName} values`,
      typeScriptUnionValues(enumName),
      pythonEnumValues(enumName)
    );
  });
}
