#!/usr/bin/env node

/**
 * CLI 入口点
 */

const path = require('path');
const { spawn } = require('child_process');

const platform = process.platform;
const arch = process.arch;

const platformMap = {
  'darwin': 'macos',
  'linux': 'linux',
  'win32': 'windows'
};

const platformKey = platformMap[platform];
const binaryName = platformKey === 'windows' ? 'agent.exe' : 'agent';
const binaryPath = path.join(__dirname, '..', 'bin', platformKey, arch, binaryName);

const fs = require('fs');
if (!fs.existsSync(binaryPath)) {
  console.error(`错误: 未找到 ${platformKey}-${arch} 的预编译程序`);
  console.error('请尝试重新安装: npm install littlezerk --rebuild');
  process.exit(1);
}

const child = spawn(binaryPath, process.argv.slice(2), {
  stdio: 'inherit'
});

child.on('exit', (code) => process.exit(code || 0));
