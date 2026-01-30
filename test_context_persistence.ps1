# Test de Persistencia de Contexto para Debug de Laptop TURNO 3
# Este test capturará exactamente qué está pasando con el contexto

$baseUrl = "http://localhost:8000"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputDir = "test_results_context_debug_$timestamp"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

function Test-Laptop-Context-Loss {
    Write-Host "`n=== PRUEBA: Laptop - Problema de Pérdida de Contexto TURNO 3 ===" -ForegroundColor Magenta
    Write-Host "Objetivo: Entender por qué TURNO 3 retorna N/A" -ForegroundColor Cyan
    
    $sessionId = [guid]::NewGuid().ToString()
    Write-Host "Session ID: $sessionId" -ForegroundColor Yellow
    
    # TURNO 1: Especificaciones Básicas
    Write-Host "`n[TURNO 1] Enviando especificaciones básicas de laptop..." -ForegroundColor Green
    $response1Obj = @{
        "user_query" = "Laptop portátil con 16GB de RAM, SSD de 512GB, procesador Intel Core i7"
        "session_id" = $sessionId
    }
    $response1 = Invoke-RestMethod -Uri "$baseUrl/classify" -Method POST -ContentType "application/json" -Body ($response1Obj | ConvertTo-Json)
    
    $code1 = $response1.hs_code
    $conf1 = $response1.confidence
    $q1_count = ($response1.questions | Measure-Object).Count
    
    Write-Host "Código: $code1 | Confianza: $conf1 | Preguntas: $q1_count" -ForegroundColor Cyan
    Write-Host "Preguntas: $($response1.questions)" -ForegroundColor Gray
    
    $result1 = @{
        turno = 1
        code = $code1
        confidence = $conf1
        questions = $response1.questions
        full_response = $response1
    }
    
    # TURNO 2: Respuesta a Preguntas + Más Detalles
    Write-Host "`n[TURNO 2] Respondiendo preguntas y agregando más detalles..." -ForegroundColor Green
    $turn2_input = "Laptop portátil con 16GB de RAM DDR5, SSD de 512GB NVMe, procesador Intel Core i7 última generación, batería de 12 horas, pantalla 4K OLED, nueva"
    
    $response2Obj = @{
        "user_query" = $turn2_input
        "session_id" = $sessionId
        "conversation_history" = @(
            @{
                "role" = "user"
                "content" = "Laptop portátil con 16GB de RAM, SSD de 512GB, procesador Intel Core i7"
            },
            @{
                "role" = "assistant"
                "content" = "Entiendo, tienes una laptop..."
            }
        )
    }
    $response2 = Invoke-RestMethod -Uri "$baseUrl/classify" -Method POST -ContentType "application/json" -Body ($response2Obj | ConvertTo-Json)
    
    $code2 = $response2.hs_code
    $conf2 = $response2.confidence
    $q2_count = ($response2.questions | Measure-Object).Count
    
    Write-Host "Código: $code2 | Confianza: $conf2 | Preguntas: $q2_count" -ForegroundColor Cyan
    Write-Host "Preguntas: $($response2.questions)" -ForegroundColor Gray
    
    $result2 = @{
        turno = 2
        code = $code2
        confidence = $conf2
        questions = $response2.questions
        full_response = $response2
    }
    
    # TURNO 3: Input Mínimo para Testear Si Retiene Contexto
    Write-Host "`n[TURNO 3] Enviando apenas confirmación - ¿Retiene clasificación anterior?" -ForegroundColor Green
    Write-Host "Input: 'Sí, es exactamente eso, laptop con especificaciones técnicas'" -ForegroundColor Gray
    
    $response3Obj = @{
        "user_query" = "Sí, es exactamente eso, laptop con especificaciones técnicas"
        "session_id" = $sessionId
        "conversation_history" = @(
            @{
                "role" = "user"
                "content" = "Laptop portátil con 16GB de RAM, SSD de 512GB, procesador Intel Core i7"
            },
            @{
                "role" = "assistant"
                "content" = "Entiendo..."
            },
            @{
                "role" = "user"
                "content" = $turn2_input
            },
            @{
                "role" = "assistant"
                "content" = "Excelente..."
            }
        )
    }
    $response3 = Invoke-RestMethod -Uri "$baseUrl/classify" -Method POST -ContentType "application/json" -Body ($response3Obj | ConvertTo-Json)
    
    $code3 = $response3.hs_code
    $conf3 = $response3.confidence
    $q3_count = ($response3.questions | Measure-Object).Count
    
    Write-Host "Código: $code3 | Confianza: $conf3 | Preguntas: $q3_count" -ForegroundColor Cyan
    Write-Host "Preguntas: $($response3.questions)" -ForegroundColor Gray
    
    if ($code3 -eq "N/A" -or $code3 -eq "9999.00") {
        Write-Host "❌ PROBLEMA CONFIRMADO: Perdió la clasificación en TURNO 3" -ForegroundColor Red
        Write-Host "   TURNO 2 tenía: $code2" -ForegroundColor Yellow
        Write-Host "   TURNO 3 tiene:  $code3" -ForegroundColor Red
    } else {
        Write-Host "✅ Contexto mantenido correctamente" -ForegroundColor Green
    }
    
    $result3 = @{
        turno = 3
        code = $code3
        confidence = $conf3
        questions = $response3.questions
        full_response = $response3
    }
    
    # TURNO 4 EXTRA: Insistir con contexto laptop
    Write-Host "`n[TURNO 4 EXTRA] Input explícito de laptop para ver si se recupera..." -ForegroundColor Green
    $response4Obj = @{
        "user_query" = "Laptop, portátil, computadora portátil con procesador i7 y 16GB RAM"
        "session_id" = $sessionId
        "conversation_history" = @(
            @{
                "role" = "user"
                "content" = "Sí, es exactamente eso, laptop con especificaciones técnicas"
            }
        )
    }
    $response4 = Invoke-RestMethod -Uri "$baseUrl/classify" -Method POST -ContentType "application/json" -Body ($response4Obj | ConvertTo-Json)
    
    $code4 = $response4.hs_code
    $conf4 = $response4.confidence
    
    Write-Host "Código: $code4 | Confianza: $conf4" -ForegroundColor Cyan
    
    if ($code4 -ne "N/A" -and $code4 -ne "9999.00") {
        Write-Host "✅ Se recuperó cuando re-ingresó contexto laptop explícito" -ForegroundColor Green
    }
    
    # Guardar resultados
    $allResults = @{
        test = "Laptop Context Loss Debug"
        session_id = $sessionId
        timestamp = $timestamp
        results = @($result1, $result2, $result3)
        analysis = @{
            turno1_ok = $code1 -eq "8471.30" -or $code1 -eq "8471.90"
            turno2_ok = $code2 -eq "8471.30" -or $code2 -eq "8471.90"
            turno3_ok = $code3 -eq "8471.30" -or $code3 -eq "8471.90"
            context_lost_in_turno3 = ($code2 -ne "N/A") -and ($code3 -eq "N/A" -or $code3 -eq "9999.00")
        }
    }
    
    $allResults | ConvertTo-Json -Depth 10 | Out-File "$outputDir\laptop_context_debug.json"
    return $allResults
}

function Test-Ambiguous-Device-Keywords {
    Write-Host "`n=== PRUEBA: Dispositivo Ambiguo - Problema de Detección de Palabras Clave ===" -ForegroundColor Magenta
    Write-Host "Objetivo: Confirmar si palabras clave laptop previenen preguntas de vehículo" -ForegroundColor Cyan
    
    $sessionId = [guid]::NewGuid().ToString()
    Write-Host "Session ID: $sessionId" -ForegroundColor Yellow
    
    # TURNO 1: Descripción que confunde (capacidad + portátil)
    Write-Host "`n[TURNO 1] Enviando descripción ambigua..." -ForegroundColor Green
    $description1 = "Portátil con capacidad de almacenamiento de 512GB, pesa 2kg, batería de 12 horas, pantalla OLED"
    Write-Host "Input: $description1" -ForegroundColor Gray
    
    $response1Obj = @{
        "user_query" = $description1
        "session_id" = $sessionId
    }
    $response1 = Invoke-RestMethod -Uri "$baseUrl/classify" -Method POST -ContentType "application/json" -Body ($response1Obj | ConvertTo-Json)
    
    $code1 = $response1.hs_code
    $conf1 = $response1.confidence
    $questions1 = $response1.questions
    
    Write-Host "Código: $code1 | Confianza: $conf1" -ForegroundColor Cyan
    Write-Host "Preguntas ($($questions1.Count)): $($questions1)" -ForegroundColor Gray
    
    # Verificar si hizo preguntas de vehículo
    $vehicle_questions = $questions1 | Where-Object { $_ -like "*vehículo*" -or $_ -like "*personas*" -or $_ -like "*transporte*" }
    
    if ($vehicle_questions.Count -gt 0) {
        Write-Host "❌ PROBLEMA: Hizo preguntas de vehículo a pesar de palabras clave laptop" -ForegroundColor Red
        Write-Host "   Palabras clave detectadas: portátil, almacenamiento, batería, pantalla OLED" -ForegroundColor Yellow
        Write-Host "   Preguntas de vehículo: $($vehicle_questions)" -ForegroundColor Red
    } else {
        Write-Host "✅ Correctamente clasificó como laptop (sin preguntas de vehículo)" -ForegroundColor Green
    }
    
    # TURNO 2: Reforzar con más palabras clave técnicas
    Write-Host "`n[TURNO 2] Reforzando con palabras clave técnicas..." -ForegroundColor Green
    $description2 = "Portátil para procesamiento de datos, 16GB RAM DDR5, SSD NVMe, procesador Ryzen, pantalla 4K"
    Write-Host "Input: $description2" -ForegroundColor Gray
    
    $response2Obj = @{
        "user_query" = $description2
        "session_id" = $sessionId
        "conversation_history" = @(
            @{
                "role" = "user"
                "content" = $description1
            },
            @{
                "role" = "assistant"
                "content" = "Entiendo..."
            }
        )
    }
    $response2 = Invoke-RestMethod -Uri "$baseUrl/classify" -Method POST -ContentType "application/json" -Body ($response2Obj | ConvertTo-Json)
    
    $code2 = $response2.hs_code
    $conf2 = $response2.confidence
    
    Write-Host "Código: $code2 | Confianza: $conf2" -ForegroundColor Cyan
    
    $allResults = @{
        test = "Ambiguous Device Keywords Debug"
        session_id = $sessionId
        timestamp = $timestamp
        results = @{
            turno1 = @{
                code = $code1
                confidence = $conf1
                questions = $questions1
            }
            turno2 = @{
                code = $code2
                confidence = $conf2
            }
        }
        analysis = @{
            had_vehicle_questions = $vehicle_questions.Count -gt 0
            resolved_in_turno2 = $code2 -eq "8471.30" -or $code2 -eq "8471.90"
        }
    }
    
    $allResults | ConvertTo-Json -Depth 10 | Out-File "$outputDir\ambiguous_device_debug.json"
    return $allResults
}

# Ejecutar pruebas
Write-Host "`n╔════════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║                     TEST DE DEBUG: PERSISTENCIA DE CONTEXTO                    ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

$laptop_results = Test-Laptop-Context-Loss
$ambiguous_results = Test-Ambiguous-Device-Keywords

# Resumen final
Write-Host "`n╔════════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║                               RESUMEN DE RESULTADOS                            ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Write-Host "`n📊 Laptop Context Persistence:" -ForegroundColor Cyan
Write-Host "   TURNO 1: $(if ($laptop_results.analysis.turno1_ok) { '✅' } else { '❌' })" -ForegroundColor $(if ($laptop_results.analysis.turno1_ok) { 'Green' } else { 'Red' })
Write-Host "   TURNO 2: $(if ($laptop_results.analysis.turno2_ok) { '✅' } else { '❌' })" -ForegroundColor $(if ($laptop_results.analysis.turno2_ok) { 'Green' } else { 'Red' })
Write-Host "   TURNO 3: $(if ($laptop_results.analysis.turno3_ok) { '✅' } else { '❌' })" -ForegroundColor $(if ($laptop_results.analysis.turno3_ok) { 'Green' } else { 'Red' })
Write-Host "   Context Loss Detected: $(if ($laptop_results.analysis.context_lost_in_turno3) { '❌ YES' } else { '✅ NO' })" -ForegroundColor $(if ($laptop_results.analysis.context_lost_in_turno3) { 'Red' } else { 'Green' })

Write-Host "`n📊 Ambiguous Device Keyword Detection:" -ForegroundColor Cyan
Write-Host "   Vehicle Questions in TURNO 1: $(if ($ambiguous_results.analysis.had_vehicle_questions) { '❌ YES' } else { '✅ NO' })" -ForegroundColor $(if ($ambiguous_results.analysis.had_vehicle_questions) { 'Red' } else { 'Green' })
Write-Host "   Resolved in TURNO 2: $(if ($ambiguous_results.analysis.resolved_in_turno2) { '✅' } else { '❌' })" -ForegroundColor $(if ($ambiguous_results.analysis.resolved_in_turno2) { 'Green' } else { 'Red' })

Write-Host "`n✅ Resultados guardados en: $outputDir" -ForegroundColor Green
Write-Host "   - laptop_context_debug.json" -ForegroundColor Gray
Write-Host "   - ambiguous_device_debug.json" -ForegroundColor Gray
