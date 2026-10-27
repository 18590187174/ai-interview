Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = 'e:\ai项目\AI模拟面试平台'
$dist = Join-Path $root 'frontend\dist'
$dest = Join-Path $root 'dist.zip'

if (-not (Test-Path $dist)) {
    Write-Error 'frontend\dist 不存在，请先执行：cd frontend && npm run build'
    exit 1
}

if (Test-Path $dest) { Remove-Item $dest -Force }

$files = Get-ChildItem -Path $dist -Recurse -File
$zip = [System.IO.Compression.ZipFile]::Open($dest, [System.IO.Compression.ZipArchiveMode]::Create)
foreach ($f in $files) {
    $rel = 'dist/' + ($f.FullName.Substring($dist.Length + 1) -replace '\\', '/')
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, $rel, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
}
$zip.Dispose()

'{0} files, size {1:N2} MB -> {2}' -f $files.Count, ((Get-Item $dest).Length / 1MB), $dest
