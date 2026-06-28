# Setup portable Python environment in the workspace

$WorkDir = "F:\Antigravity\ICR-OMR-Reading"
$PythonDir = Join-Path $WorkDir "python_env"
$ZipFile = Join-Path $PythonDir "python-embed.zip"
$PythonUrl = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$GetPipFile = Join-Path $PythonDir "get-pip.py"

Write-Host "Creating Python environment directory at $PythonDir..."
if (-not (Test-Path $PythonDir)) {
    New-Item -ItemType Directory -Path $PythonDir | Out-Null
}

Write-Host "Downloading portable Python from $PythonUrl..."
Invoke-WebRequest -Uri $PythonUrl -OutFile $ZipFile

Write-Host "Extracting Python files..."
Expand-Archive -Path $ZipFile -DestinationPath $PythonDir -Force
Remove-Item -Path $ZipFile

Write-Host "Configuring Python path to enable site-packages..."
$PthFile = Join-Path $PythonDir "python310._pth"
if (Test-Path $PthFile) {
    $Content = Get-Content $PthFile
    # Uncomment 'import site'
    $NewContent = $Content -replace '^#import site', 'import site'
    $NewContent | Set-Content $PthFile
    Write-Host "Uncommented 'import site' in $PthFile."
} else {
    Write-Warning "Could not find python310._pth!"
}

Write-Host "Downloading get-pip.py..."
Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipFile

Write-Host "Installing pip..."
$PythonExe = Join-Path $PythonDir "python.exe"
& $PythonExe $GetPipFile

Write-Host "Installing required libraries from requirements.txt..."
$PipExe = Join-Path $PythonDir "Scripts\pip.exe"
$ReqFile = Join-Path $WorkDir "requirements.txt"
& $PipExe install -r $ReqFile

Write-Host "Python environment setup complete!"
