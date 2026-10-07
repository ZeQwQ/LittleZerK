#!/usr/bin/env node

/**
 * postinstall 脚本
 * 自动从 GitHub Releases 下载对应平台的预编译二进制
 */

const path = require('path');
const fs = require('fs');
const https = require('https');
const zlib = require('zlib');
const { execSync } = require('child_process');

const platform = process.platform;
const arch = process.arch;

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

const ext = platformKey === 'windows' ? 'zip' : 'tar.gz';
const archiveName = `littlezerk-${platformKey}-${arch}.${ext}`;
const binaryName = platformKey === 'windows' ? 'agent.exe' : 'agent';

// 获取包版本
const pkgVersion = require('../package.json').version;
const repoOwner = 'ZeQwQ';
const repoName = 'LittleZerK_ver.0.3';

// 目标目录
const targetBinDir = path.join(__dirname, '..', 'bin', `${platformKey}-${arch}`);
const targetAgentPath = path.join(targetBinDir, binaryName);

// 检查是否已有二进制
if (fs.existsSync(targetAgentPath)) {
  console.log(`✅ 找到预编译二进制: ${targetAgentPath}`);
  process.exit(0);
}

// 确保目录存在
fs.mkdirSync(targetBinDir, { recursive: true });

// 下载文件
function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        // 重定向
        downloadFile(response.headers.location, dest).then(resolve).catch(reject);
        return;
      }
      if (response.statusCode !== 200) {
        reject(new Error(`下载失败: ${response.statusCode}`));
        return;
      }
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

// 解压 tar.gz
function extractTarGz(tarPath, destDir) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    fs.createReadStream(tarPath)
      .pipe(zlib.createGunzip())
      .on('data', (chunk) => chunks.push(chunk))
      .on('end', () => {
        // 简单的 tar 解压（只处理最外层）
        const Buffer = require('buffer').Buffer;
        const data = Buffer.concat(chunks);
        let i = 0;
        while (i < data.length) {
          // tar header is 512 bytes
          if (data.slice(i, i + 100).toString().includes('ustar')) {
            const header = data.slice(i, i + 512);
            const fileName = header.slice(0, 100).toString().replace(/\0/g, '').trim();
            const fileSizeStr = header.slice(124, 136).toString().replace(/\0/g, '').trim();
            const fileSize = parseInt(fileSizeStr, 8);

            if (fileName && fileSize > 0) {
              const content = data.slice(i + 512, i + 512 + fileSize);
              const outPath = path.join(destDir, path.basename(fileName));
              fs.writeFileSync(outPath, content);
            }
            i += 512 + Math.ceil(fileSize / 512) * 512;
          } else {
            break;
          }
        }
        resolve();
      })
      .on('error', reject);
  });
}

// 解压 zip (Windows)
function extractZip(zipPath, destDir) {
  try {
    // 使用 PowerShell 解压
    const cmd = `powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${destDir}' -Force"`;
    execSync(cmd, { stdio: 'inherit' });
    return Promise.resolve();
  } catch (err) {
    return Promise.reject(err);
  }
}

async function main() {
  console.log(`📦 正在为 ${platformKey}-${arch} 下载预编译二进制...`);
  console.log(`版本: ${pkgVersion}`);

  const apiUrl = `https://api.github.com/repos/${repoOwner}/${repoName}/releases/tags/v${pkgVersion}`;

  try {
    // 获取 Release 信息
    const response = await new Promise((resolve, reject) => {
      https.get(apiUrl, { headers: { 'User-Agent': 'littlezerk-postinstall' } }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve(JSON.parse(data)));
      }).on('error', reject);
    });

    // 找到对应平台的资产
    const asset = response.assets?.find(a => a.name === archiveName);
    if (!asset) {
      throw new Error(`未找到 ${archiveName}，请确认该版本已发布`);
    }

    console.log(`⬇️  下载: ${asset.browser_download_url}`);

    const tempArchive = path.join(__dirname, '..', '..', 'temp_download.' + ext);
    await downloadFile(asset.browser_download_url, tempArchive);

    console.log(`📂 解压到: ${targetBinDir}`);

    if (ext === 'zip') {
      await extractZip(tempArchive, targetBinDir);
    } else {
      await extractTarGz(tempArchive, targetBinDir);
    }

    // 清理临时文件
    fs.unlinkSync(tempArchive);

    console.log(`✅ 安装完成! 运行 'littlezerk' 启动`);

  } catch (err) {
    console.error(`❌ 安装失败: ${err.message}`);
    console.log(`
手动安装:
1. 访问 https://github.com/${repoOwner}/${repoName}/releases
2. 下载 ${archiveName}
3. 解压到: ${path.join(__dirname, '..', 'bin')}
`);
    process.exit(1);
  }
}

main();
