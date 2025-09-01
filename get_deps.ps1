# get_deps.ps1

# Define an array of URLs for the .tar.gz files to download
$urls = @(
    "https://quantag-it.com/pub/libs/qpp.tar.gz"
    "https://quantag-it.com/pub/libs/json.tar.gz"
    "https://quantag-it.com/pub/libs/eigen.tar.gz"
    "https://quantag-it.com/pub/libs/boost.tar.gz"
    "https://quantag-it.com/pub/libs/openblas.tar.gz"
    "https://quantag-it.com/pub/libs/curl.tar.gz"
)

# Specify the target directory where files will be unpacked
$target_dir = "third_party"

# Create target directory if it doesn't exist
if (-not (Test-Path $target_dir)) {
    New-Item -ItemType Directory -Path $target_dir | Out-Null
}

foreach ($url in $urls) {
    # Get the file name from the URL
    $file_name = Split-Path $url -Leaf

    Write-Host "Downloading $file_name..."
    Invoke-WebRequest -Uri $url -OutFile $file_name -UseBasicParsing

    Write-Host "Unpacking $file_name to $target_dir..."
    # Use tar (available on Windows 10+ with Git or Windows Subsystem for Linux)
    tar -xzf $file_name -C $target_dir

    # Remove the archive after extraction
    Remove-Item $file_name
}

Write-Host "All files have been downloaded and unpacked to $target_dir."
