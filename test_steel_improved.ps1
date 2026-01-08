$base_url = 'http://localhost:8000'
$conversation_id = 'test-steel-' + [guid]::NewGuid().ToString()

Write-Host 'Testing Steel Laminate Flow with Improved Detection' -ForegroundColor Cyan
Write-Host "Conversation ID: $conversation_id" -ForegroundColor Gray

# Step 1: Product type
Write-Host -ForegroundColor Yellow '=== Step 1: Mention láminas de acero ==='
$response1 = Invoke-WebRequest -Uri "$base_url/classify" -Method POST -ContentType 'application/json' -Body (@{
    user_query = 'Tengo láminas de acero'
    conversation_id = $conversation_id
} | ConvertTo-Json) -SkipHttpErrorCheck

$data1 = $response1.Content | ConvertFrom-Json
Write-Host "Status: $($response1.StatusCode)" -ForegroundColor Cyan
if ($response1.StatusCode -eq 200) {
    Write-Host "Codes:" -ForegroundColor Cyan
    Write-Host ($data1.candidates | ConvertTo-Json -Depth 1)
    Write-Host "Missing fields:" -ForegroundColor Cyan
    Write-Host ($data1.missing_fields | ConvertTo-Json)
} else {
    Write-Host "Error: $($response1.Content)" -ForegroundColor Red
}

Start-Sleep -Milliseconds 500

# Step 2: Dimensions and process
Write-Host -ForegroundColor Yellow '=== Step 2: Add espesor 10mm, laminadas en caliente ==='
$response2 = Invoke-WebRequest -Uri "$base_url/classify" -Method POST -ContentType 'application/json' -Body (@{
    user_query = 'con espesor de 10 mm, ancho de 1 metro, laminadas en caliente'
    conversation_id = $conversation_id
} | ConvertTo-Json) -SkipHttpErrorCheck

$data2 = $response2.Content | ConvertFrom-Json
Write-Host "Status: $($response2.StatusCode)" -ForegroundColor Cyan
if ($response2.StatusCode -eq 200) {
    Write-Host "Codes:" -ForegroundColor Cyan
    Write-Host ($data2.candidates | ConvertTo-Json -Depth 1)
    Write-Host "Missing fields:" -ForegroundColor Cyan
    Write-Host ($data2.missing_fields | ConvertTo-Json)
} else {
    Write-Host "Error: $($response2.Content)" -ForegroundColor Red
}

Start-Sleep -Milliseconds 500

# Step 3: Coating
Write-Host -ForegroundColor Yellow '=== Step 3: Add galvanizadas ==='
$response3 = Invoke-WebRequest -Uri "$base_url/classify" -Method POST -ContentType 'application/json' -Body (@{
    user_query = 'y galvanizadas'
    conversation_id = $conversation_id
} | ConvertTo-Json) -SkipHttpErrorCheck

$data3 = $response3.Content | ConvertFrom-Json
Write-Host "Status: $($response3.StatusCode)" -ForegroundColor Cyan
if ($response3.StatusCode -eq 200) {
    Write-Host "Codes:" -ForegroundColor Cyan
    Write-Host ($data3.candidates | ConvertTo-Json -Depth 1)
    Write-Host "Missing fields:" -ForegroundColor Cyan
    Write-Host ($data3.missing_fields | ConvertTo-Json)
} else {
    Write-Host "Error: $($response3.Content)" -ForegroundColor Red
}
Write-Host "Expected: missing_fields should be empty or minimal []" -ForegroundColor Green
