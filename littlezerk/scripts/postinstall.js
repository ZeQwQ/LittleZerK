#!/usr/bin/env node

/**
 * postinstall 脚本
 * 检查预编译二进制是否存在，不存在则提示用户
 */

const path = require('path');
const fs = require('fs');

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

if (!fs.existsSync(binaryPath)) {
  console.log(`
⚠️  未找到预编译二进制文件

平台: ${platformKey} (${arch})
路径: ${binaryPath}

请手动从 GitHub Releases 下载对应平台的压缩包：
https://github.com/YOUR_GITHUB/littlezerk/releases

或者从源码编译：
https://github.com/YOUR_GITHUB/littlezerk#build-from-source
`);
}
