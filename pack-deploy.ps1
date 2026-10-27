Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = 'e:\ai项目\AI模拟面试平台'
$dest = 'e:\ai项目\AI模拟面试平台-deploy.zip'

if (Test-Path $dest) { Remove-Item $dest -Force }

$excludeDirs = @('node_modules', '.venv', 'dist', 'var', '__pycache__', '.git', '.pytest_cache', 'egg-info', '.codebuddy', 'openspec', '.ruff_cache')
$excludeExt = @('.pyc', '.db', '.log', '.png', '.ps1')

$files = Get-ChildItem -Path $root -Recurse -File -Force | Where-Object {
    $full = $_.FullName
    $rel = $full.Substring($root.Length + 1)
    $skip = $false
    foreach ($d in $excludeDirs) {
        if ($rel -match ('^' + [regex]::Escape($d) + '(\\|$)') -or $rel -match ('\\' + [regex]::Escape($d) + '(\\|$)')) { $skip = $true; break }
    }
    if (-not $skip -and $excludeExt -contains $_.Extension.ToLower()) { $skip = $true }
    -not $skip
}

$zip = [System.IO.Compression.ZipFile]::Open($dest, [System.IO.Compression.ZipArchiveMode]::Create)
foreach ($f in $files) {
    $rel = $f.FullName.Substring($root.Length + 1) -replace '\\', '/'
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, $rel, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
}
$zip.Dispose()

$size = (Get-Item $dest).Length / 1MB
'{0} files, size {1:N2} MB' -f $files.Count, $size

# 校验：列出包内的迁移文件
$check = [System.IO.Compression.ZipFile]::OpenRead($dest)
"--- migrations in zip ---"
$check.Entries.FullName | Where-Object { $_ -like 'backend/alembic/versions/*' }
"--- key files ---"
$check.Entries.FullName | Where-Object { $_ -in @('docker-compose.prod.yml', 'frontend/nginx.conf', 'backend/Dockerfile', 'frontend/Dockerfile') }
$check.Dispose()
