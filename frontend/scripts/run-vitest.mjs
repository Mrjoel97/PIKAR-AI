import path from 'node:path'
import { EventEmitter } from 'node:events'
import { spawnSync } from 'node:child_process'
import { createRequire, syncBuiltinESMExports } from 'node:module'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const initialCwd = process.cwd()

if (initialCwd.toLowerCase() !== root.toLowerCase() && process.env.PIKAR_VITEST_REEXEC !== '1') {
  const result = spawnSync(process.execPath, [__filename, ...process.argv.slice(2)], {
    cwd: root,
    stdio: 'inherit',
    env: {
      ...process.env,
      PIKAR_VITEST_REEXEC: '1',
    },
  })
  process.exit(result.status ?? 1)
}

process.chdir(root)
if (process.platform === 'win32') {
  process.env.ESBUILD_BINARY_PATH ||= path.resolve(root, 'node_modules', '@esbuild', 'win32-x64', 'esbuild.exe')
}

const require = createRequire(import.meta.url)
const childProcess = require('node:child_process')
const originalExec = childProcess.exec
const originalSpawn = childProcess.spawn
const esbuildBinary = path.resolve(root, 'node_modules', '@esbuild', 'win32-x64', 'esbuild.exe')

childProcess.spawn = function patchedSpawn(command, args, options) {

  if (process.platform === 'win32' && typeof command === 'string') {
    const normalizedCommand = command.replaceAll('/', '\\').toLowerCase()
    if (normalizedCommand.endsWith('node_modules\\esbuild\\bin\\esbuild') || normalizedCommand.endsWith('node_modules\\esbuild\\bin\\esbuild.exe')) {
      return originalSpawn.call(this, esbuildBinary, args, options)
    }
  }

  return originalSpawn.call(this, command, args, options)
}

childProcess.exec = function patchedExec(command, ...args) {
  if (process.platform === 'win32' && typeof command === 'string' && command.trim().toLowerCase() === 'net use') {
    const callback = args.find((arg) => typeof arg === 'function')
    const child = new EventEmitter()
    child.stdout = new EventEmitter()
    child.stderr = new EventEmitter()
    child.pid = 0
    child.kill = () => true

    queueMicrotask(() => {
      callback?.(null, '', '')
      child.emit('exit', 0)
      child.emit('close', 0)
    })

    return child
  }

  return originalExec.call(this, command, ...args)
}

syncBuiltinESMExports()

const [{ parseCLI, startVitest }, { default: react }] = await Promise.all([
  import('vitest/node'),
  import('@vitejs/plugin-react'),
])

const argv = ['vitest', ...process.argv.slice(2)]
const parsed = parseCLI(argv)

const ctx = await startVitest(
  'test',
  parsed.filter,
  {
    ...parsed.options,
    config: false,
    environment: parsed.options.environment ?? 'jsdom',
    globals: parsed.options.globals ?? true,
    pool: parsed.options.pool ?? 'threads',
  },
  {
    root,
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(root, 'src'),
      },
    },
  },
)

const failed = ctx?.state?.getCountOfFailedTests?.() ?? 0
await ctx?.close?.()
process.exit(failed > 0 ? 1 : 0)

