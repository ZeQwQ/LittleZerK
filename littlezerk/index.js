#!/usr/bin/env node

/**
 * littlezerk - 小小泽 AI 助手
 * npm 包入口
 */

const path = require('path');
const { spawn } = require('child_process');

// 检测平台
const platform = process.platform;
const arch = process.arch;

// 平台映射
const platformMap = {
  'darwin': 'macos',
  'linux': 'linux',
  'win32': 'windows'
};

const platformKey = platformMap[platform];
if (!platformKey) {
  console.error(`不支持的平台: ${platform}`);
  process.exit(1);
}

// 预编译二进制路径
const binaryName = platformKey === 'windows' ? 'agent.exe' : 'agent';
const binaryPath = path.join(__dirname, 'bin', platformKey, arch, binaryName);

const fs = require('fs');
if (!fs.existsSync(binaryPath)) {
  console.error(`未找到预编译文件: ${binaryPath}`);
  console.error('请运行: npm install littlezerk --rebuild');
  process.exit(1);
}

// 启动 agent
const child = spawn(binaryPath, process.argv.slice(2), {
  stdio: 'inherit',
  env: process.env
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
