#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Caminho do arquivo version.json
const versionPath = path.join(__dirname, '../version.json');

// Lê o arquivo atual
const versionData = JSON.parse(fs.readFileSync(versionPath, 'utf8'));

// Incrementa a versão PATCH
const [major, minor, patch] = versionData.version.split('.').map(Number);
const newVersion = `${major}.${minor}.${patch + 1}`;

// Pega a mensagem do último commit
let commitMessage = '';
try {
  commitMessage = execSync('git log -1 --pretty=%B', { encoding: 'utf8' }).trim();
} catch (error) {
  commitMessage = 'Atualização automática';
}

// Atualiza a data
const today = new Date().toISOString().split('T')[0];

// Adiciona a nova versão ao changelog
const newChangelogEntry = {
  version: newVersion,
  date: today,
  changes: [commitMessage]
};

// Atualiza o objeto
versionData.version = newVersion;
versionData.lastUpdate = today;
versionData.changelog.unshift(newChangelogEntry);

// Mantém apenas as últimas 10 versões no changelog
if (versionData.changelog.length > 10) {
  versionData.changelog = versionData.changelog.slice(0, 10);
}

// Salva o arquivo atualizado
fs.writeFileSync(versionPath, JSON.stringify(versionData, null, 2) + '\n', 'utf8');

console.log(`✅ Versão atualizada: ${versionData.version}`);
console.log(`📝 Changelog: ${commitMessage}`);
