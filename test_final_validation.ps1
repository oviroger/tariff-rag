# Test Final de Validación - POST FIX
# Prueba 5 categorías de productos para verificar TODO funciona correctamente

Write-Host "`n╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           TEST FINAL: VALIDACIÓN EXHAUSTIVA POST-FIX                   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

function Test-Product {
    param(
        [string]$ProductName,
        [string]$Query1,
        [string]$Query2,
        [string]$Query3,
        [string]$ExpectedCode
    )
    
    Write-Host "═════════════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "[$ProductName]" -ForegroundColor Magenta
    Write-Host "═════════════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    
    $sessionId = [guid]::NewGuid().ToString()
    $results = @()
    
    # TURNO 1
    $r1 = Invoke-RestMethod "http://localhost:8000/classify" -Method POST -ContentType "application/json" `
      -Body (@{ 
        "user_query" = $Query1
        "session_id" = $sessionId 
      } | ConvertTo-Json)
    
    $results += @{ turno = 1; code = $r1.top_candidates[0].code; conf = $r1.top_candidates[0].confidence; desc = $r1.top_candidates[0].description }
    Write-Host "`n[TURNO 1] Query: '$Query1'" -ForegroundColor Gray
    Write-Host "  Código: $($r1.top_candidates[0].code) (Conf: $([math]::Round($r1.top_candidates[0].confidence * 100))%)" -ForegroundColor $(if ($r1.top_candidates[0].code -like "$ExpectedCode*") { "Green" } else { "Yellow" })
    Write-Host "  Descripción: $($r1.top_candidates[0].description)" -ForegroundColor Gray
    if ($r1.missing_fields.Count -gt 0) {
        Write-Host "  Preguntas: $($r1.missing_fields.Count)" -ForegroundColor Cyan
    }
    
    # TURNO 2
    $r2 = Invoke-RestMethod "http://localhost:8000/classify" -Method POST -ContentType "application/json" `
      -Body (@{
        "user_query" = $Query2
        "session_id" = $sessionId
        "conversation_history" = @(
            @{ "user" = $Query1; "assistant" = "Entiendo..." }
        )
      } | ConvertTo-Json -Depth 5)
    
    $results += @{ turno = 2; code = $r2.top_candidates[0].code; conf = $r2.top_candidates[0].confidence; desc = $r2.top_candidates[0].description }
    Write-Host "`n[TURNO 2] Query: '$Query2'" -ForegroundColor Gray
    Write-Host "  Código: $($r2.top_candidates[0].code) (Conf: $([math]::Round($r2.top_candidates[0].confidence * 100))%)" -ForegroundColor $(if ($r2.top_candidates[0].code -like "$ExpectedCode*") { "Green" } else { "Yellow" })
    
    # TURNO 3
    $r3 = Invoke-RestMethod "http://localhost:8000/classify" -Method POST -ContentType "application/json" `
      -Body (@{
        "user_query" = $Query3
        "session_id" = $sessionId
        "conversation_history" = @(
            @{ "user" = $Query1; "assistant" = "..." },
            @{ "user" = $Query2; "assistant" = "..." }
        )
      } | ConvertTo-Json -Depth 5)
    
    $results += @{ turno = 3; code = $r3.top_candidates[0].code; conf = $r3.top_candidates[0].confidence; desc = $r3.top_candidates[0].description }
    Write-Host "`n[TURNO 3] Query: '$Query3'" -ForegroundColor Gray
    Write-Host "  Código: $($r3.top_candidates[0].code) (Conf: $([math]::Round($r3.top_candidates[0].confidence * 100))%)" -ForegroundColor $(if ($r3.top_candidates[0].code -like "$ExpectedCode*") { "Green" } else { "Yellow" })
    
    # ANÁLISIS
    $all_correct = $results | Where-Object { $_.code -like "$ExpectedCode*" }
    if ($all_correct.Count -eq 3) {
        Write-Host "`n✅ ÉXITO: Correcta en los 3 turnos" -ForegroundColor Green
        return $true
    } elseif ($all_correct.Count -ge 2) {
        Write-Host "`n🟡 PARCIAL: Correcta en $($all_correct.Count)/3 turnos" -ForegroundColor Yellow
        return $false
    } else {
        Write-Host "`n❌ FALLA: Correcta en $($all_correct.Count)/3 turnos" -ForegroundColor Red
        return $false
    }
}

# EJECUTAR TESTS
$results_summary = @()

# 1. LAPTOP (FIXED)
$laptop_ok = Test-Product `
    -ProductName "LAPTOP (FIXED)" `
    -Query1 "Laptop portátil 16GB RAM SSD 512GB" `
    -Query2 "Procesador i7, pantalla 4K OLED, batería 12 horas" `
    -Query3 "Sí, es nueva" `
    -ExpectedCode "8471"
$results_summary += @{ product = "Laptop"; ok = $laptop_ok }

# 2. AUTOBÚS (Verificar que vehículos siguen funcionando)
$bus_ok = Test-Product `
    -ProductName "AUTOBÚS (Vehículos)" `
    -Query1 "Autobús para 50 personas" `
    -Query2 "Diesel, año 2023" `
    -Query3 "Nuevo" `
    -ExpectedCode "8702"
$results_summary += @{ product = "Autobús"; ok = $bus_ok }

# 3. LAVADORA (Electrodoméstico)
$washer_ok = Test-Product `
    -ProductName "LAVADORA (Electrodoméstico)" `
    -Query1 "Lavadora automática de carga frontal" `
    -Query2 "8kg, 1400 rpm, clase A" `
    -Query3 "Nueva" `
    -ExpectedCode "8450"
$results_summary += @{ product = "Lavadora"; ok = $washer_ok }

# 4. MICROONDAS
$microwave_ok = Test-Product `
    -ProductName "MICROONDAS (Electrodoméstico)" `
    -Query1 "Microondas con grill" `
    -Query2 "1000W, función vapor" `
    -Query3 "Digital" `
    -ExpectedCode "8516"
$results_summary += @{ product = "Microondas"; ok = $microwave_ok }

# 5. DISPOSITIVO AMBIGUO
$ambiguous_ok = Test-Product `
    -ProductName "DISPOSITIVO AMBIGUO (Laptop specs)" `
    -Query1 "Portátil para procesamiento de datos, 512GB almacenamiento" `
    -Query2 "RAM DDR5, procesador Ryzen, pantalla 4K" `
    -Query3 "Para programación profesional" `
    -ExpectedCode "8471"
$results_summary += @{ product = "Dispositivo Ambiguo"; ok = $ambiguous_ok }

# RESUMEN FINAL
Write-Host "`n╔═══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║                         RESUMEN FINAL                                   ║" -ForegroundColor Yellow
Write-Host "╚═══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

$successful = @($results_summary | Where-Object { $_.ok -eq $true })
$total = $results_summary.Count

Write-Host "`n📊 Productos probados: $total"
Write-Host "✅ Éxito: $($successful.Count)"
Write-Host "❌ Falla: $($total - $successful.Count)"
Write-Host "📈 Tasa de éxito: $([math]::Round($successful.Count / $total * 100))%`n"

$results_summary | ForEach-Object {
    $status = $(if ($_.ok) { "✅" } else { "❌" })
    Write-Host "$status $($_.product)" -ForegroundColor $(if ($_.ok) { "Green" } else { "Red" })
}

Write-Host "`n$(if ($successful.Count -eq $total) { '🎉 ¡TODOS LOS TESTS PASARON!' } else { '⚠️ Algunos tests requieren revisión' })" -ForegroundColor $(if ($successful.Count -eq $total) { "Green" } else { "Yellow" })
