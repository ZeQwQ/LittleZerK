#!/usr/bin/env node

/**
 * postinstall 脚本
 * 自动从 GitHub Releases 下载对应平台的预编译二进制
 */

const path = require('path');
const fs = require('fs');
const https = require('https');
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

// 包版本
const pkg = require('../package.json');
const pkgVersion = pkg.version;
const repoOwner = (pkg.littlezerk && pkg.littlezerk.owner) || 'ZeQwQ';
const repoName = (pkg.littlezerk && pkg.littlezerk.repo) || 'LittleZerK';

// bin/ 是解压根目录：压缩包内已包含 <platform>-<arch>/ 这一层
const binRoot = path.join(__dirname, '..', 'bin');
const targetBinDir = path.join(binRoot, `${platformKey}-${arch}`);
const targetAgentPath = path.join(targetBinDir, binaryName);

const hasLocalBinary = fs.existsSync(targetAgentPath);

console.log(`📦 littlezerk ${pkgVersion} - ${platformKey}-${arch}`);

if (hasLocalBinary) {
  console.log(`🔄 检测到已安装的二进制，将尝试从 Release 获取 v${pkgVersion} 更新`);
}

// ─────────────────────────────────────────────────────────────
// 下载
// ─────────────────────────────────────────────────────────────

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        downloadFile(response.headers.location, dest).then(resolve).catch(reject);
        return;
      }
      if (response.statusCode !== 200) {
        reject(new Error(`下载失败: HTTP ${response.statusCode}`));
        return;
      }
      const file = fs.createWriteStream(dest);
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
      file.on('error', reject);
    }).on('error', reject);
  });
}

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'littlezerk-postinstall' } }, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error(`解析 GitHub API 响应失败: ${data.slice(0, 200)}`));
        }
      });
    }).on('error', reject);
  });
}

// ─────────────────────────────────────────────────────────────
// 解压
// ─────────────────────────────────────────────────────────────

function extractTarGz(tarPath, destDir) {
  try {
    execSync(`tar -xzf "${tarPath}" -C "${destDir}"`, { stdio: 'inherit' });
    return true;
  } catch (err) {
    console.error(`❌ tar 解压失败: ${err.message}`);
    return false;
  }
}

function extractZip(zipPath, destDir) {
  try {
    execSync(
      `powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${destDir}' -Force"`,
      { stdio: 'inherit' }
    );
    return true;
  } catch (err) {
    console.error(`❌ zip 解压失败: ${err.message}`);
    return false;
  }
}

/**
 * 压缩包内含顶层目录 <platform>-<arch>/，若个别环境解压出嵌套目录，
 * 这里做一次归一化，保证最终路径是 bin/<platform>-<arch>/<binary>
 */
function normalizeLayout() {
  if (fs.existsSync(targetAgentPath)) return true;

  const nested = path.join(targetBinDir, `${platformKey}-${arch}`, binaryName);
  if (fs.existsSync(nested)) {
    console.log('🔧 修正嵌套目录结构...');
    fs.renameSync(nested, targetAgentPath);
    return true;
  }
  return false;
}

// ─────────────────────────────────────────────────────────────
// 主流程
// ─────────────────────────────────────────────────────────────

async function main() {
  const apiUrl = `https://api.github.com/repos/${repoOwner}/${repoName}/releases/tags/v${pkgVersion}`;
  const tempArchive = path.join(__dirname, '..', '..', `temp_download.${ext}`);

  try {
    console.log(`⬇️  查询 Release: v${pkgVersion}`);
    const response = await fetchJson(apiUrl);

    if (!response || response.message) {
      throw new Error(`获取 Release 失败: ${response && response.message}`);
    }

    const asset = (response.assets || []).find((a) => a.name === archiveName);
    if (!asset) {
      const available = (response.assets || []).map((a) => a.name).join(', ') || '（无）';
      throw new Error(`未找到 ${archiveName}，该 Release 现有资产: ${available}`);
    }

    console.log(`⬇️  下载: ${asset.browser_download_url}`);
    await downloadFile(asset.browser_download_url, tempArchive);

    fs.mkdirSync(binRoot, { recursive: true });

    // 解压到 bin/ 根目录（压缩包自带 <platform>-<arch>/ 顶层目录）
    const ok = ext === 'zip'
      ? extractZip(tempArchive, binRoot)
      : extractTarGz(tempArchive, binRoot);

    if (ok && normalizeLayout() && fs.existsSync(targetAgentPath)) {
      console.log(`✅ 安装完成: ${targetAgentPath}`);
      console.log(`✅ 运行 'littlezerk' 启动`);
      return;
    }

    throw new Error('解压后未找到可执行文件');
  } catch (err) {
    console.error(`❌ ${err.message}`);

    // 有本地二进制时降级：网络不通 / Release 无资产时仍可使用
    if (hasLocalBinary) {
      console.warn(`⚠️  使用已存在的本地二进制: ${targetAgentPath}`);
      console.warn(`⚠️  如需最新版本，请访问 https://github.com/${repoOwner}/${repoName}/releases 手动下载`);
      return;
    }

    console.error(`
手动安装:
1. 访问 https://github.com/${repoOwner}/${repoName}/releases/tag/v${pkgVersion}
2. 下载 ${archiveName}
3. 解压到 ${binRoot}  （压缩包内含 ${platformKey}-${arch}/ 目录）
`);
    process.exit(1);
  } finally {
    if (fs.existsSync(tempArchive)) {
      try { fs.unlinkSync(tempArchive); } catch (e) { /* 忽略清理失败 */ }
    }
  }
}

main();
