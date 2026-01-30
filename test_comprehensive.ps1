#!/usr/bin/env pwsh
# Test Comprehensivo - Múltiples productos y especificaciones complejas

$API_URL = "http://localhost:8000/classify"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$results = @()

function Test-Product {
    param(
        [string]$ProductName,
        [array]$Queries
    )
    
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "🧪 TEST: $ProductName" -ForegroundColor Green
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
    
    $session_id = [guid]::NewGuid().ToString()
    $product_result = @{
        Product = $ProductName
        SessionId = $session_id
        Turnos = @()
    }
    
    foreach ($i in 0..($Queries.Count - 1)) {
        $query = $Queries[$i]
        $turno = $i + 1
        
        Write-Host ""
        Write-Host "📍 TURNO $turno" -ForegroundColor Yellow
        Write-Host "Query: $query" -ForegroundColor White
        
        try {
            $response = Invoke-WebRequest -Uri $API_URL `
                -Method POST `
                -ContentType "application/json" `
                -Body (@{ user_query = $query; session_id = $session_id } | ConvertTo-Json) `
                -ErrorAction Stop
            
            $data = $response.Content | ConvertFrom-Json
            
            $top_code = if ($data.top_candidates.Count -gt 0) { $data.top_candidates[0].code } else { "N/A" }
            $confidence = if ($data.top_candidates.Count -gt 0) { [math]::Round($data.top_candidates[0].confidence * 100, 0) } else { 0 }
            $questions = $data.missing_fields.Count
            
            Write-Host "  ✅ Código: $top_code ($confidence%)" -ForegroundColor Green
            Write-Host "  📋 Preguntas: $questions" -ForegroundColor Cyan
            
            if ($questions -gt 0) {
                Write-Host "  Detalles:" -ForegroundColor White
                foreach ($field in $data.missing_fields) {
                    Write-Host "    • $field" -ForegroundColor Gray
                }
            }
            
            if ($data.warnings -and $data.warnings.Count -gt 0) {
                Write-Host "  ⚠️  Warnings:" -ForegroundColor Yellow
                foreach ($warning in $data.warnings) {
                    if ($warning -match "Detectado cambio de categoría|motor|categoria") {
                        Write-Host "    ⚠️  $warning" -ForegroundColor Yellow
                    }
                }
            }
            
            $product_result.Turnos += @{
                Turno = $turno
                Query = $query
                Code = $top_code
                Confidence = $confidence
                Questions = $questions
                MissingFields = $data.missing_fields
                HasCategoryWarning = ($data.warnings | Where-Object { $_ -match "categoría|motor" }).Count -gt 0
            }
        }
        catch {
            Write-Host "  ❌ Error: $_" -ForegroundColor Red
        }
    }
    
    return $product_result
}

# ============ TESTS ============

# TEST 1: LAPTOP CON ESPECIFICACIONES COMPLEJAS
$laptop_tests = @(
    "Necesito importar una computadora portátil",
    "Es una Dell XPS 13 de 2024, muy nueva, con pantalla OLED de 4K",
    "Tiene 32GB de RAM DDR5 y SSD NVMe de 1TB, procesador Intel Core i9-13900K"
)
$laptop_result = Test-Product -ProductName "Laptop con Especificaciones Técnicas" -Queries $laptop_tests
$results += $laptop_result

# TEST 2: LAVADORA CON DETALLES TÉCNICOS
$lavadora_tests = @(
    "Quiero clasificar una lavadora automática",
    "Es marca LG, frontal, carga de 12 kg, ciclo rápido",
    "Voltaje 220V, capacidad 12 kg, función vapor, garantía 5 años"
)
$lavadora_result = Test-Product -ProductName "Lavadora Automática (Especificada)" -Queries $lavadora_tests
$results += $lavadora_result

# TEST 3: VEHÍCULO CON MÚLTIPLES DETALLES
$vehicle_tests = @(
    "Necesito clasificar un vehículo",
    "Es un autobús tipo escolar",
    "Tiene capacidad para 48 personas, motor diesel, nuevo, 6 cilindros, 6000cc"
)
$vehicle_result = Test-Product -ProductName "Autobús Escolar (Especificado)" -Queries $vehicle_tests
$results += $vehicle_result

# TEST 4: PRODUCTO AMBIGUO QUE PODRÍA CONFUNDIRSE
$ambiguous_tests = @(
    "Quiero clasificar un dispositivo",
    "Es portátil, pesa 2 kg, tiene batería de 12 horas",
    "Es para procesamiento de datos, tiene capacidad de almacenamiento de 512GB"
)
$ambiguous_result = Test-Product -ProductName "Dispositivo Ambiguo (SSD + Capacidad)" -Queries $ambiguous_tests
$results += $ambiguous_result

# TEST 5: MICROONDAS (ESPECIALES)
$microwave_tests = @(
    "Necesito clasificar un microondas",
    "Es un horno microondas de 800W",
    "Capacidad de 25 litros, tiene función grill y convección, nuevo"
)
$microwave_result = Test-Product -ProductName "Microondas con Funciones Especiales" -Queries $microwave_tests
$results += $microwave_result

# ============ RESUMEN FINAL ============
Write-Host ""
Write-Host "╔════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║ 📊 RESUMEN DE PRUEBAS COMPREHENSIVAS 📊       ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

foreach ($result in $results) {
    Write-Host "📦 $($result.Product)" -ForegroundColor Cyan
    
    $turno_count = $result.Turnos.Count
    $avg_questions = if ($turno_count -gt 0) { 
        [math]::Round(($result.Turnos | Measure-Object -Property Questions -Average).Average, 1)
    } else { 0 }
    
    $final_turno = $result.Turnos[-1]
    $final_code = $final_turno.Code
    $final_confidence = $final_turno.Confidence
    $has_warnings = ($result.Turnos | Where-Object { $_.HasCategoryWarning }).Count -gt 0
    
    Write-Host "  Turnos: $turno_count | Promedio Preguntas: $avg_questions | Código Final: $final_code ($final_confidence%)" -ForegroundColor White
    
    if ($has_warnings) {
        Write-Host "  ⚠️  Validación de categoría activada (categoría confusa detectada)" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Categoría clara (sin conflictos)" -ForegroundColor Green
    }
    
    Write-Host ""
}

Write-Host "✅ Pruebas completadas: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
