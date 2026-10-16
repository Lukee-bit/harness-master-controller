# Install Cursor Master Controller Light (Windows).
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$CursorHome = if ($env:CURSOR_HOME) { $env:CURSOR_HOME } else { Join-Path $env:USERPROFILE ".cursor" }
$PluginDest = Join-Path $CursorHome "plugins\local\always-use-all-skills"
$ScriptsDest = Join-Path $CursorHome "scripts\master-controller"
$SkillsDest = Join-Path $CursorHome "skills"
$RulesDir = Join-Path $CursorHome "rules"
$BackupRoot = Join-Path $CursorHome "backups"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

function Write-Info([string]$Message) { Write-Host $Message }

function Get-PythonCommand {
    $candidates = @(
        @{ Test = { Get-Command py -ErrorAction SilentlyContinue }; Cmd = "py -3" },
        @{ Test = { Get-Command python -ErrorAction SilentlyContinue }; Cmd = "python" },
        @{ Test = { Get-Command python3 -ErrorAction SilentlyContinue }; Cmd = "python3" }
    )
    foreach ($candidate in $candidates) {
        if (& $candidate.Test) { return $candidate.Cmd }
    }
    throw "Python 3 not found."
}

function Copy-Tree([string]$Source, [string]$Destination, [switch]$Mirror) {
    if (-not (Test-Path $Source)) { throw "Missing source directory: $Source" }
    if ($Mirror -and (Test-Path $Destination)) {
        Remove-Item -LiteralPath $Destination -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Copy-Item -Path (Join-Path $Source "*") -Destination $Destination -Recurse -Force
}

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function New-HookCommand([string]$ScriptPath, [string]$Python) {
    return "$Python `"$ScriptPath`""
}

Write-Info "=== Cursor Master Controller Light Installer (Windows) ==="
Write-Info "CURSOR_HOME=$CursorHome"

$vendorSkills = Join-Path $Root "vendor\skills"
if (-not (Test-Path $vendorSkills)) {
    throw "No bundled skills in vendor\skills\. Run bundle-from-cursor.sh first."
}
$hasSkill = Get-ChildItem -Path $vendorSkills -Filter SKILL.md -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $hasSkill) { throw "vendor\skills exists but contains no SKILL.md files." }

$python = Get-PythonCommand

New-Item -ItemType Directory -Force -Path (Join-Path $CursorHome "state") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $CursorHome "plugins\local") | Out-Null
New-Item -ItemType Directory -Force -Path $RulesDir | Out-Null
New-Item -ItemType Directory -Force -Path $ScriptsDest | Out-Null
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

if ((Test-Path $SkillsDest) -and (Get-ChildItem -Path $SkillsDest -Filter SKILL.md -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    $BackupDir = Join-Path $BackupRoot "skills-full-$Stamp"
    Write-Info "Backing up existing skills to $BackupDir ..."
    Copy-Tree -Source $SkillsDest -Destination $BackupDir
    Write-Utf8NoBom (Join-Path $BackupRoot "skills-full-latest.txt") $BackupDir
}

Write-Info "Installing light skills (mirror)..."
Copy-Tree -Source $vendorSkills -Destination $SkillsDest -Mirror

$vendorPlugins = Join-Path $Root "vendor\plugins"
if (Test-Path $vendorPlugins) {
    Write-Info "Installing bundled plugins..."
    $localSrc = Join-Path $vendorPlugins "local"
    if (Test-Path $localSrc) {
        Get-ChildItem -Path $localSrc -Directory | ForEach-Object {
            $dest = Join-Path $CursorHome "plugins\local\$($_.Name)"
            Copy-Tree -Source $_.FullName -Destination $dest -Mirror
        }
    }
    $cacheSrc = Join-Path $vendorPlugins "cache"
    if (Test-Path $cacheSrc) {
        $cacheDest = Join-Path $CursorHome "plugins\cache"
        New-Item -ItemType Directory -Force -Path $cacheDest | Out-Null
        Copy-Item -Path (Join-Path $cacheSrc "*") -Destination $cacheDest -Recurse -Force
    }
}

Write-Info "Installing light master plugin..."
Copy-Tree -Source (Join-Path $Root "plugin\always-use-all-skills") -Destination $PluginDest -Mirror

$vendorRules = Join-Path $Root "vendor\rules"
if (Test-Path $vendorRules) {
    Write-Info "Installing user rules..."
    Copy-Tree -Source $vendorRules -Destination $RulesDir
}

Write-Info "Installing hook scripts..."
Copy-Tree -Source (Join-Path $Root "scripts") -Destination $ScriptsDest -Mirror

$session = New-HookCommand (Join-Path $ScriptsDest "session_start.py") $python
$route = New-HookCommand (Join-Path $ScriptsDest "route_prompt.py") $python
$track = New-HookCommand (Join-Path $ScriptsDest "track_reads.py") $python
$stop = New-HookCommand (Join-Path $ScriptsDest "stop_enforce.py") $python
$inject = New-HookCommand (Join-Path $ScriptsDest "inject_task_skills.py") $python
$sub = New-HookCommand (Join-Path $ScriptsDest "subagent_policy.py") $python
$tab = New-HookCommand (Join-Path $ScriptsDest "tab_prose_lint.py") $python

$hooksJson = @"
{
  "version": 1,
  "hooks": {
    "sessionStart": [ { "command": "$($session -replace '\\','\\')" } ],
    "beforeSubmitPrompt": [ { "command": "$($route -replace '\\','\\')", "matcher": "UserPromptSubmit" } ],
    "preToolUse": [ { "command": "$($inject -replace '\\','\\')", "matcher": "Task" } ],
    "postToolUse": [ { "command": "$($track -replace '\\','\\')", "matcher": "Read" } ],
    "subagentStart": [ { "command": "$($sub -replace '\\','\\')" } ],
    "stop": [ { "command": "$($stop -replace '\\','\\')", "loop_limit": 3 } ],
    "afterTabFileEdit": [ { "command": "$($tab -replace '\\','\\')" } ]
  }
}
"@

# Build hooks.json with escaped paths properly
$hooksObj = [ordered]@{
  version = 1
  hooks = [ordered]@{
    sessionStart = @(@{ command = $session })
    beforeSubmitPrompt = @(@{ command = $route; matcher = "UserPromptSubmit" })
    preToolUse = @(@{ command = $inject; matcher = "Task" })
    postToolUse = @(@{ command = $track; matcher = "Read" })
    subagentStart = @(@{ command = $sub })
    stop = @(@{ command = $stop; loop_limit = 3 })
    afterTabFileEdit = @(@{ command = $tab })
  }
}
$hooksPath = Join-Path $CursorHome "hooks.json"
($hooksObj | ConvertTo-Json -Depth 6) | Set-Content -Path $hooksPath -Encoding UTF8

$ruleSrc = Join-Path $PluginDest "rules\always-use-all-skills.mdc"
if (Test-Path $ruleSrc) {
    Copy-Item $ruleSrc (Join-Path $RulesDir "always-use-all-skills.mdc") -Force
}

$memRule = Join-Path $PluginDest "rules\project-memory.mdc"
if (Test-Path $memRule) {
    Copy-Item $memRule (Join-Path $RulesDir "project-memory.mdc") -Force
}
$memSkill = Join-Path $Root "plugin\always-use-all-skills\skills\project-memory\SKILL.md"
if (Test-Path $memSkill) {
    $dest = Join-Path $SkillsDest "my-workflow\project-memory"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item $memSkill (Join-Path $dest "SKILL.md") -Force
}
$mcpRec = Join-Path $Root "config\mcp\mcp-light-recommended.json"
if (Test-Path $mcpRec) {
    Copy-Item $mcpRec (Join-Path $CursorHome "mcp-light-recommended.json") -Force
}

$obsoletePool = Join-Path $CursorHome "advisor-light-model-pool.json"
if (Test-Path $obsoletePool) { Remove-Item $obsoletePool -Force }
$advReadme = Join-Path $Root "config\advisor\README.md"
if (Test-Path $advReadme) {
    Copy-Item $advReadme (Join-Path $CursorHome "advisor-light-README.md") -Force
}
$tmpl = Join-Path $Root "templates"
if (Test-Path $tmpl) {
    $tmplDest = Join-Path $CursorHome "templates\light-memory"
    New-Item -ItemType Directory -Force -Path $tmplDest | Out-Null
    Copy-Item -Path (Join-Path $tmpl "*") -Destination $tmplDest -Recurse -Force
}

$pluginHooks = Join-Path $PluginDest "hooks"
New-Item -ItemType Directory -Force -Path $pluginHooks | Out-Null
Copy-Item $hooksPath (Join-Path $pluginHooks "hooks.json") -Force

$lightSkill = Join-Path $PluginDest "skills\always-use-all-skills\SKILL.md"
$destSkill = Join-Path $SkillsDest "my-workflow\always-use-all-skills\SKILL.md"
New-Item -ItemType Directory -Force -Path (Split-Path $destSkill) | Out-Null
Copy-Item $lightSkill $destSkill -Force

Write-Info ""
Write-Info "=== Light install complete ==="
Write-Info "Verify: $python `"$(Join-Path $ScriptsDest 'verify_setup.py')`""
Write-Info "Reload Cursor and enable rules/plugins in Customize."
Write-Info "Enable in Customize: Always Use All Skills (Light), Humanizer Stack, Ponytail, cursor-team-kit, thermos, Advisor."

$setupHeadroom = Join-Path $Root "scripts\setup-headroom.sh"
if (Test-Path $setupHeadroom) {
    Write-Info "Running Headroom force setup..."
    bash $setupHeadroom
}
$hrReadme = Join-Path $Root "config\headroom\README.md"
if (Test-Path $hrReadme) {
    Copy-Item $hrReadme (Join-Path $CursorHome "headroom-README.md") -Force
}

# Token optimizer stack (rtk, sqz, squeez, mcptoon, context-mode, jcodemunch, cce)
$setupToken = Join-Path $Root "scripts\setup-token-optimizers.sh"
if (Test-Path $setupToken) {
    Write-Info "Running token optimizer stack setup..."
    bash $setupToken
}

# Portable MCP config: resolves tool paths on THIS machine.
$setupMcp = Join-Path $Root "scripts\setup-mcp.sh"
if (Test-Path $setupMcp) {
    Write-Info "Generating portable MCP config..."
    bash $setupMcp
}
Write-Info "Note: native Windows does not support the RTK hook or lumen plugin binary; those tokens tools are macOS/Linux only."

Write-Info "Advisor is judgment-based and never auto-enabled. cursor-subagent-creator is a judgment skill (no plugin enable needed)."
