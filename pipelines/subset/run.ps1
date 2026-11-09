param(
    [int]$Size = 5000,
    [int]$Seed = 42,
    [int]$Brands = 80,
    [double]$FocusFraction = 0.2,
    [string]$Image = 'm4r:b030afac47d1',
    [string]$Sources = '',
    [string]$Out = ''
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not $Sources) { $Sources = Join-Path $workspace 'data\subset-sources.json' }
if (-not $Out) { $Out = Join-Path $workspace "data\subsets\silver-n$Size-seed$Seed" }
if (Test-Path -LiteralPath $Out) { throw "Output already exists: $Out. Set -Out to a new directory." }
$sourceConfig = Get-Content -LiteralPath $Sources -Raw | ConvertFrom-Json
$dockerSources = @{ pedia_root = '/pedia'; domains = @{} }
$mounts = @('--mount', "type=bind,source=$PSScriptRoot,target=/subset,readonly",
            '--mount', "type=bind,source=$($sourceConfig.pedia_root),target=/pedia,readonly")
foreach ($domain in @('food','fragrance')) {
    $entry = $sourceConfig.domains.$domain
    $dockerSources.domains[$domain] = @{ legacy_bridge_sha256 = $entry.legacy_bridge_sha256; original_silver = $entry.silver; silver_snapshot = $entry.silver_snapshot }
    foreach ($field in @('silver','native_bridge','legacy_bridge')) {
        $file = (Resolve-Path -LiteralPath $entry.$field).Path
        $target = "/inputs/$domain-$field.parquet"
        $mounts += @('--mount', "type=bind,source=$file,target=$target,readonly")
        $dockerSources.domains[$domain][$field] = $target
    }
}
$runRecord = Join-Path $workspace ("tasks\subset-run-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runRecord | Out-Null
$dockerConfig = Join-Path $runRecord 'sources.json'
$dockerSources | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $dockerConfig -Encoding UTF8
$outParent = Split-Path -Parent $Out
New-Item -ItemType Directory -Path $outParent -Force | Out-Null
$outName = Split-Path -Leaf $Out
$mounts += @('--mount', "type=bind,source=$dockerConfig,target=/inputs/sources.json,readonly",
             '--mount', "type=bind,source=$outParent,target=/output")
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 @mounts $Image python /subset/subset.py `
    --sources /inputs/sources.json --out "/output/$outName" --size $Size --seed $Seed --brands $Brands --focus-fraction $FocusFraction
if ($LASTEXITCODE -ne 0) { throw "Extractor exited $LASTEXITCODE; partial output preserved at $Out" }
Write-Output "Silver subsets: $Out"
