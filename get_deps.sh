#!/bin/bash

# Define an array of URLs for the .zip files to download
urls=(
    "https://quantag-it.com/pub/libs/qpp.tar.gz"
    "https://quantag-it.com/pub/libs/json.tar.gz"
    "https://quantag-it.com/pub/libs/eigen.tar.gz"
    "https://quantag-it.com/pub/libs/boost.tar.gz"
)

# Specify the target directory where files will be unpacked
target_dir="third_party"

# Create the target directory if it doesn't exist
#mkdir -p "$target_dir"

# Loop through each URL to download and unzip the files
for url in "${urls[@]}"; do
    # Get the file name from the URL
    file_name=$(basename "$url")
    
    # Download the .zip file using wget with -c to resume interrupted downloads
    echo "Downloading $file_name..."
    wget -c "$url" -O "$file_name"
    
    # Unzip the downloaded file to the target directory
    echo "Unpacking $file_name to $target_dir..."
    tar -xzvf "$file_name" -C "$target_dir"

    # Optionally, remove the .zip file after extraction
    rm "$file_name"
done

echo "All files have been downloaded and unpacked to $target_dir."
