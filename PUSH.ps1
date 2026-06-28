$container = "bluesky-review-poster"
$baseDir = "T:\bluesky-review-poster"

# Clean array - added missing commas between elements
$syncItems = @(
    "app.py",
    "BlueSky.py",
    "backloggd.py",
    "letterboxd.py",
    "serializd.py",
    "goodreads.py",
    "Auth.py",
    "alerts.py",
    "requirements.txt"
)

if (docker ps -q -f name=$container) {
    foreach ($item in $syncItems) {
        # Source is the specific file or folder on your T: drive
        $sourcePath = Join-Path $baseDir $item
        
        # DESTINATION: We target the container's root directory.
        # This tells Docker: "Put the item 'main' into '/'," which triggers a merge.
        $destPath = "${container}:/app/" 

        if (Test-Path $sourcePath) {
            Write-Host "Pushing $item to container..." -ForegroundColor Yellow
            docker cp $sourcePath $destPath
        } else {
            Write-Warning "Source not found: $sourcePath"
        }
    }
    
    Write-Host "`nRestarting container to apply changes..." -ForegroundColor Magenta
    docker restart $container
    
    Write-Host "Deploy Complete! Structure should be flat." -ForegroundColor Green
} else {
    Write-Error "Container $container is not running. Start it with 'docker compose up -d' first."
}