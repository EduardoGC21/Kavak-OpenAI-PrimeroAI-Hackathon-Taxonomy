param(
    [int]$Size = 500,
    [ValidateSet('food','fragrance','both')][string]$Domain = 'both',
    [string]$Image = 'm4r:b030afac47d1',
    [string]$Sources = '',
    [string]$GoldSources = '',
    [string]$Out = ''
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
if (-not $Sources) { $Sources = Join-Path $workspace 'data\subset-sources.json' }
if (-not $GoldSources) { $GoldSources = Join-Path $workspace 'data\gold-sources.json' }
if (-not $Out) { $Out = Join-Path $workspace "data\subsets\gold-batches-n$Size" }
if (Test-Path -LiteralPath $Out) { throw "Output already exists: $Out. Set -Out to a new directory." }
$sourceConfig = Get-Content -LiteralPath $Sources -Raw | ConvertFrom-Json
$goldConfig = Get-Content -LiteralPath $GoldSources -Raw | ConvertFrom-Json
$dockerSources = @{ domains = @{} }
$mounts = @('--mount', "type=bind,source=$PSScriptRoot,target=/subset,readonly")
$domains = if ($Domain -eq 'both') { @('food','fragrance') } else { @($Domain) }
foreach ($sourceDomain in $domains) {
    $entry = $sourceConfig.domains.$sourceDomain
    $gold = $goldConfig.domains.$sourceDomain
    $target = "/inputs/$sourceDomain-silver.parquet"
    $file = (Resolve-Path -LiteralPath $entry.silver).Path
    $mounts += @('--mount', "type=bind,source=$file,target=$target,readonly")
    $dockerEntry = @{ silver = $target; original_silver = $entry.silver; gold_release = $gold.release; views = @{}; historical_sources = @() }
    $historyIndex = 0
    foreach ($history in $gold.unlabeled_history) {
        $file = (Resolve-Path -LiteralPath $history).Path
        $target = "/inputs/$sourceDomain-history-$historyIndex.parquet"
        $mounts += @('--mount', "type=bind,source=$file,target=$target,readonly")
        $dockerEntry.historical_sources += @{ path = $target; original_path = $history }
        $historyIndex++
    }
    foreach ($property in $gold.views.PSObject.Properties) {
        $viewName = $property.Name
        $viewFiles = @{ labels_sha256 = $property.Value.labels_sha256 }
        foreach ($field in @('labels','assignments','members','products')) {
            if (-not $property.Value.$field) { continue }
            $file = (Resolve-Path -LiteralPath $property.Value.$field).Path
            $target = "/gold/$sourceDomain/$viewName/$field.parquet"
            $mounts += @('--mount', "type=bind,source=$file,target=$target,readonly")
            $viewFiles[$field] = $target
            $viewFiles["original_$field"] = $property.Value.$field
        }
        $dockerEntry.views[$viewName] = $viewFiles
    }
    if ($dockerEntry.views.Count -eq 0) { throw "No Gold views configured for $sourceDomain" }
    $dockerSources.domains[$sourceDomain] = $dockerEntry
}
$runRecord = Join-Path $workspace ("tasks\gold-batch-run-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runRecord | Out-Null
$dockerConfig = Join-Path $runRecord 'sources.json'
$dockerSources | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $dockerConfig -Encoding UTF8
$outParent = Split-Path -Parent $Out
New-Item -ItemType Directory -Path $outParent -Force | Out-Null
$outName = Split-Path -Leaf $Out
$mounts += @('--mount', "type=bind,source=$dockerConfig,target=/inputs/sources.json,readonly",
             '--mount', "type=bind,source=$outParent,target=/output")
$arguments = @('--sources','/inputs/sources.json','--out',"/output/$outName",'--size',"$Size",'--domain',$Domain)
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 @mounts $Image python /subset/gold.py @arguments
if ($LASTEXITCODE -ne 0) { throw "Gold batch extractor exited $LASTEXITCODE; partial output preserved at $Out" }
Write-Output "Original Gold subsets: $Out"
Write-Output "Run configuration: $dockerConfig"
