# Test completo del flujo de vehículos
# Este script prueba la conversación paso a paso

$API_URL = "http://localhost:8000/classify"
$conv_id = [guid]::NewGuid().ToString()

Write-Host "`n=== TEST DE FLUJO CONVERSACIONAL: VEHÍCULOS ===" -ForegroundColor Cyan
Write-Host "Conversation ID: $conv_id`n" -ForegroundColor Gray

# Función para hacer una petición
function Invoke-ClassifyRequest {
    param(
        [string]$Query,
        [array]$History = @(),
        [string]$ConvId
    )
    
    $body = @{
        user_query = $Query
        conversation_history = $History
        conversation_id = $ConvId
        top_k = 3
    } | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri $API_URL -Method Post -Body $body -ContentType "application/json"
        return $response
    } catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
        return $null
    }
}

# Función para mostrar resultados
function Show-Response {
    param(
        [string]$Query,
        [object]$Response,
        [int]$Step
    )
    
    Write-Host "[$Step] PREGUNTA: " -ForegroundColor Yellow -NoNewline
    Write-Host "$Query" -ForegroundColor White
    
    if ($Response) {
        $candidates = $Response.top_candidates
        $missing = $Response.missing_fields
        
        if ($candidates -and $candidates.Count -gt 0) {
            Write-Host "    CÓDIGOS SUGERIDOS:" -ForegroundColor Green
            foreach ($cand in $candidates) {
                Write-Host "    - $($cand.code): $($cand.description)" -ForegroundColor White
            }
        }
        
        if ($missing -and $missing.Count -gt 0) {
            Write-Host "    INFORMACIÓN FALTANTE:" -ForegroundColor Magenta
            foreach ($m in $missing) {
                Write-Host "    - $m" -ForegroundColor White
            }
        }
        
        if ((!$candidates -or $candidates.Count -eq 0) -and (!$missing -or $missing.Count -eq 0)) {
            Write-Host "    [Sin candidatos ni campos faltantes]" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# Inicializar historial
$history = @()

# PASO 1: Pregunta inicial sobre vehículos
Write-Host "`n--- PASO 1: Pregunta inicial ---" -ForegroundColor Cyan
$query1 = "¿Cuál es la partida arancelaria de los vehículos?"
$resp1 = Invoke-ClassifyRequest -Query $query1 -History $history -ConvId $conv_id
Show-Response -Query $query1 -Response $resp1 -Step 1

# Actualizar historial
$history += @{
    user = $query1
    assistant = "Necesito más información..."
    timestamp = (Get-Date).ToString("o")
}

# PASO 2: Especificar uso (personas)
Write-Host "--- PASO 2: Especificar uso ---" -ForegroundColor Cyan
$query2 = "Es para transporte de personas"
$resp2 = Invoke-ClassifyRequest -Query $query2 -History $history -ConvId $conv_id
Show-Response -Query $query2 -Response $resp2 -Step 2

# Actualizar historial
$history += @{
    user = $query2
    assistant = "Necesito tipo específico..."
    timestamp = (Get-Date).ToString("o")
}

# PASO 3: Especificar tipo de vehículo
Write-Host "--- PASO 3: Especificar tipo ---" -ForegroundColor Cyan
$query3 = "Es un autobús"
$resp3 = Invoke-ClassifyRequest -Query $query3 -History $history -ConvId $conv_id
Show-Response -Query $query3 -Response $resp3 -Step 3

# Actualizar historial
$history += @{
    user = $query3
    assistant = "Necesito tipo de motor..."
    timestamp = (Get-Date).ToString("o")
}

# PASO 4: Especificar motor
Write-Host "--- PASO 4: Especificar motor ---" -ForegroundColor Cyan
$query4 = "Es a diesel"
$resp4 = Invoke-ClassifyRequest -Query $query4 -History $history -ConvId $conv_id
Show-Response -Query $query4 -Response $resp4 -Step 4

# Actualizar historial
$history += @{
    user = $query4
    assistant = "Necesito cilindrada..."
    timestamp = (Get-Date).ToString("o")
}

# PASO 5: Especificar cilindrada
Write-Host "--- PASO 5: Especificar cilindrada ---" -ForegroundColor Cyan
$query5 = "Cilindrada de 6000 cc"
$resp5 = Invoke-ClassifyRequest -Query $query5 -History $history -ConvId $conv_id
Show-Response -Query $query5 -Response $resp5 -Step 5

# Actualizar historial
$history += @{
    user = $query5
    assistant = "Necesito número de plazas..."
    timestamp = (Get-Date).ToString("o")
}

# PASO 6: Especificar plazas
Write-Host "--- PASO 6: Especificar plazas ---" -ForegroundColor Cyan
$query6 = "Es para 50 pasajeros"
$resp6 = Invoke-ClassifyRequest -Query $query6 -History $history -ConvId $conv_id
Show-Response -Query $query6 -Response $resp6 -Step 6

# PASO 7: Verificar si NO aparece el texto genérico
Write-Host "`n=== VALIDACIÓN ===" -ForegroundColor Cyan
$has_generic = $false
if ($resp6.missing_fields) {
    foreach ($field in $resp6.missing_fields) {
        if ($field -match "Dimensiones relevantes|Proceso de fabricación|norma aplicable") {
            $has_generic = $true
            break
        }
    }
}

if ($has_generic) {
    Write-Host "❌ FALLO: Todavía aparece texto genérico en missing_fields" -ForegroundColor Red
    Write-Host "Missing fields: $($resp6.missing_fields -join ', ')" -ForegroundColor Yellow
} else {
    Write-Host "✅ ÉXITO: No hay texto genérico" -ForegroundColor Green
    if ($resp6.top_candidates -and $resp6.top_candidates.Count -gt 0) {
        Write-Host "✅ Se devolvieron códigos HS" -ForegroundColor Green
    } elseif ($resp6.missing_fields -and $resp6.missing_fields.Count -gt 0) {
        Write-Host "⚠️  Todavía pide información, pero es específica de vehículos" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  No hay candidatos ni missing_fields (posible error de LLM)" -ForegroundColor Yellow
    }
}

Write-Host "`n=== FIN DEL TEST ===" -ForegroundColor Cyan
