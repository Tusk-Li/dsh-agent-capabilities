import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

export const name = 'agent-capabilities';
export const inject = ['skills'];
export const skillsDirectory = fileURLToPath(new URL('./skills/', import.meta.url));

export function browserExecutable(config = {}, env = process.env, platform = process.platform) {
  if (config.executablePath) {
    if (!existsSync(config.executablePath)) throw new Error('Configured browser executable does not exist');
    return config.executablePath;
  }
  const candidates = platform === 'win32'
    ? [env.PROGRAMFILES && join(env.PROGRAMFILES, 'Google/Chrome/Application/chrome.exe'),
       env['PROGRAMFILES(X86)'] && join(env['PROGRAMFILES(X86)'], 'Microsoft/Edge/Application/msedge.exe'),
       env.LOCALAPPDATA && join(env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe')]
    : platform === 'darwin' ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
      : ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  return candidates.filter(Boolean).find(existsSync);
}

export async function apply(ctx, config = {}) {
  for (const flag of ['enableBrowser', 'enableDesktop']) {
    if (config[flag] !== undefined && typeof config[flag] !== 'boolean') throw new Error(`${flag} must be boolean`);
  }
  await ctx.plugin(await import('@deepseek-ai/dsh-skill-filesystem'), {
    providerName: 'agent-capabilities', includeDefaultRoots: false, customSkillDirs: [skillsDirectory],
  });
  if (config.enableBrowser) {
    await ctx.plugin(await import('@deepseek-ai/dsh-browser-use'));
    const executablePath = browserExecutable(config);
    await ctx.plugin(await import('@deepseek-ai/dsh-experimental-browser-use-playwright-mcp'), {
      mode: 'launch', headless: true, toolCallTimeoutMs: 60000,
      ...(executablePath ? { executablePath } : {}),
    });
  }
  if (config.enableDesktop) {
    await ctx.plugin(await import('@deepseek-ai/dsh-computer-use'));
    await ctx.plugin(await import('@deepseek-ai/dsh-experimental-computer-use-cua-driver-native'));
  }
}
