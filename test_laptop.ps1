#!/usr/bin/env pwsh
# Test script para verificar mejora con OTRA MERCANCÍA MAS SIMPLE (Laptop)

$API_URL = "http://localhost:8000/classify"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$output_dir = "d:\MAESTRIA - copia\tariff-rag\test_results_laptop_$timestamp"

New-Item -ItemType Directory -Path $output_dir -Force | Out-Null

Write-Host "=== PRUEBA CON OTRA MERCANCÍA: LAPTOP ===" -ForegroundColor Green
Write-Host "Timestamp: $timestamp" -ForegroundColor Cyan
Write-Host "Output Directory: $output_dir" -ForegroundColor Cyan
Write-Host ""

# TURNO 1: Query inicial sobre laptop
Write-Host "📍 TURNO 1: Query inicial sobre laptop" -ForegroundColor Yellow
$turno1_query = "Necesito clasificar una computadora portátil que voy a importar"
Write-Host "Query: $turno1_query" -ForegroundColor White

$turno1_response = Invoke-WebRequest -Uri $API_URL `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{ user_query = $turno1_query } | ConvertTo-Json) `
    -ErrorAction Stop

$turno1_data = $turno1_response.Content | ConvertFrom-Json

# Guardar TURNO 1
$turno1_file = "$output_dir\TURNO_1_RESPONSE.json"
$turno1_response.Content | Out-File -Path $turno1_file -Encoding UTF8
Write-Host "✓ TURNO 1 guardado" -ForegroundColor Green

# Extraer session_id y mostrar resumen
$session_id = $turno1_data.session_id
$top_code = $turno1_data.top_candidates[0].code
$confidence = $turno1_data.top_candidates[0].confidence
$missing_fields = $turno1_data.missing_fields

Write-Host ""
Write-Host "RESPUESTA TURNO 1:" -ForegroundColor Cyan
Write-Host "  Session ID: $session_id" -ForegroundColor White
Write-Host "  Código Top: $top_code (confianza: $confidence)" -ForegroundColor White
Write-Host "  Missing Fields:" -ForegroundColor Yellow
foreach ($field in $missing_fields) {
    Write-Host "    • $field" -ForegroundColor White
}

$field_count = $missing_fields.Count
if ($field_count -ge 2) {
    Write-Host "✅ Múltiples preguntas: $field_count" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Preguntas: $field_count" -ForegroundColor White
}
Write-Host ""

# TURNO 2: Responder con especificaciones
Write-Host "📍 TURNO 2: Responder con marca y modelo" -ForegroundColor Yellow
$turno2_query = "Es una Dell XPS 13, es nueva"
Write-Host "Query: $turno2_query" -ForegroundColor White

$turno2_response = Invoke-WebRequest -Uri $API_URL `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{ user_query = $turno2_query; session_id = $session_id } | ConvertTo-Json) `
    -ErrorAction Stop

$turno2_data = $turno2_response.Content | ConvertFrom-Json

# Guardar TURNO 2
$turno2_file = "$output_dir\TURNO_2_RESPONSE.json"
$turno2_response.Content | Out-File -Path $turno2_file -Encoding UTF8
Write-Host "✓ TURNO 2 guardado" -ForegroundColor Green

Write-Host ""
Write-Host "RESPUESTA TURNO 2:" -ForegroundColor Cyan
$turno2_code = $turno2_data.top_candidates[0].code
$turno2_confidence = $turno2_data.top_candidates[0].confidence
$turno2_missing = $turno2_data.missing_fields

Write-Host "  Código Top: $turno2_code (confianza: $turno2_confidence)" -ForegroundColor White
Write-Host "  Missing Fields:" -ForegroundColor Yellow
if ($turno2_missing.Count -eq 0) {
    Write-Host "    • (Vacío - clasificación completa)" -ForegroundColor Green
} else {
    foreach ($field in $turno2_missing) {
        Write-Host "    • $field" -ForegroundColor White
    }
}
Write-Host ""

# TURNO 3: Responder con más detalles opcionales
Write-Host "📍 TURNO 3: Responder con detalles de almacenamiento" -ForegroundColor Yellow
$turno3_query = "Tiene SSD de 512GB y 16GB de RAM"
Write-Host "Query: $turno3_query" -ForegroundColor White

$turno3_response = Invoke-WebRequest -Uri $API_URL `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{ user_query = $turno3_query; session_id = $session_id } | ConvertTo-Json) `
    -ErrorAction Stop

$turno3_data = $turno3_response.Content | ConvertFrom-Json

# Guardar TURNO 3
$turno3_file = "$output_dir\TURNO_3_RESPONSE.json"
$turno3_response.Content | Out-File -Path $turno3_file -Encoding UTF8
Write-Host "✓ TURNO 3 guardado" -ForegroundColor Green

Write-Host ""
Write-Host "RESPUESTA TURNO 3:" -ForegroundColor Cyan
$turno3_code = $turno3_data.top_candidates[0].code
$turno3_confidence = $turno3_data.top_candidates[0].confidence
$turno3_missing = $turno3_data.missing_fields

Write-Host "  Código Final: $turno3_code (confianza: $turno3_confidence)" -ForegroundColor Green
Write-Host "  Missing Fields:" -ForegroundColor Yellow
if ($turno3_missing.Count -eq 0) {
    Write-Host "    • (Vacío - clasificación completa)" -ForegroundColor Green
} else {
    foreach ($field in $turno3_missing) {
        Write-Host "    • $field" -ForegroundColor White
    }
}
Write-Host ""

# Capturar logs
Write-Host "📍 Capturando datos de ejecución..." -ForegroundColor Yellow
$docker_logs = docker logs rag-api 2>&1 | Select-Object -Last 100
$docker_logs | Out-File -Path "$output_dir\DOCKER_LOGS.txt" -Encoding UTF8

$redis_key = "chat:$session_id"
$redis_data = docker exec rag-redis redis-cli GET $redis_key 2>&1
$redis_data | Out-File -Path "$output_dir\REDIS_CONVERSATION.json" -Encoding UTF8
Write-Host "✓ Datos capturados" -ForegroundColor Green

Write-Host ""
Write-Host "=== RESUMEN FINAL - LAPTOP ===" -ForegroundColor Green
Write-Host "TURNO 1:" -ForegroundColor Cyan
Write-Host "  Code: $top_code | Confidence: $confidence | Questions: $field_count" -ForegroundColor White
Write-Host ""
Write-Host "TURNO 2:" -ForegroundColor Cyan
Write-Host "  Code: $turno2_code | Confidence: $turno2_confidence | Questions: $($turno2_missing.Count)" -ForegroundColor White
Write-Host ""
Write-Host "TURNO 3 (FINAL):" -ForegroundColor Cyan
Write-Host "  Code: $turno3_code | Confidence: $turno3_confidence | Questions: $($turno3_missing.Count)" -ForegroundColor Green
Write-Host ""
Write-Host "📂 Archivos guardados en: $output_dir" -ForegroundColor Green
