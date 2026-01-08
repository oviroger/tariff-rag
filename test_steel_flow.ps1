# Test completo del flujo de clasificación de acero laminado
# Este script prueba la conversación paso a paso

$API_URL = "http://localhost:8000/classify"
$conv_id = [guid]::NewGuid().ToString()

Write-Host "`n=== TEST DE FLUJO CONVERSACIONAL: LÁMINAS DE ACERO ===" -ForegroundColor Cyan
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

# PASO 1: Pregunta inicial sobre acero
Write-Host "`n--- PASO 1: Pregunta inicial ---" -ForegroundColor Cyan
$query1 = "Quiero clasificar láminas de acero"
$resp1 = Invoke-ClassifyRequest -Query $query1 -History $history -ConvId $conv_id
Show-Response -Query $query1 -Response $resp1 -Step 1

# Actualizar historial
$history += @{
    user = $query1
    assistant = "Necesito más información..."
    timestamp = (Get-Date).ToString("o")
}

# PASO 2: Especificar espesor
Write-Host "--- PASO 2: Especificar espesor ---" -ForegroundColor Cyan
$query2 = "Tiene un espesor de 10 mm"
$resp2 = Invoke-ClassifyRequest -Query $query2 -History $history -ConvId $conv_id
Show-Response -Query $query2 -Response $resp2 -Step 2

# Actualizar historial
$history += @{
    user = $query2
    assistant = "Necesito tipo de laminado..."
    timestamp = (Get-Date).ToString("o")
}

# PASO 3: Especificar tipo de laminado y recubrimiento
Write-Host "--- PASO 3: Especificar laminado y galvanizado ---" -ForegroundColor Cyan
$query3 = "Son láminas de acero laminadas en caliente y son galvanizadas"
$resp3 = Invoke-ClassifyRequest -Query $query3 -History $history -ConvId $conv_id
Show-Response -Query $query3 -Response $resp3 -Step 3

# VALIDACIÓN
Write-Host "`n=== VALIDACIÓN ===" -ForegroundColor Cyan

if ($resp3.top_candidates -and $resp3.top_candidates.Count -gt 0) {
    $main_code = $resp3.top_candidates[0].code
    
    # Verificar que sea 7208
    if ($main_code -match "^7208") {
        Write-Host "✅ ÉXITO: Código correcto (7208)" -ForegroundColor Green
    } else {
        Write-Host "❌ FALLO: Código incorrecto (esperado 7208, obtenido $main_code)" -ForegroundColor Red
    }
    
    # Verificar que NO pida recubrimiento si ya se proporcionó
    if ($resp3.missing_fields) {
        $missing_text = $resp3.missing_fields -join ", "
        if ($missing_text -match "recubrimiento|galvanizado|pintado") {
            Write-Host "⚠️  ADVERTENCIA: Todavía pide recubrimiento aunque ya se especificó galvanizado" -ForegroundColor Yellow
            Write-Host "Missing fields: $missing_text" -ForegroundColor Yellow
        } else {
            Write-Host "✅ ÉXITO: No pide recubrimiento nuevamente" -ForegroundColor Green
            Write-Host "Missing fields: $missing_text" -ForegroundColor Gray
        }
    } else {
        Write-Host "✅ ÉXITO: Sin missing_fields o clasificación completa" -ForegroundColor Green
    }
} else {
    Write-Host "❌ FALLO: No se devolvieron códigos HS" -ForegroundColor Red
    if ($resp3.missing_fields) {
        Write-Host "Missing fields: $($resp3.missing_fields -join ', ')" -ForegroundColor Yellow
    }
}

Write-Host "`n=== FIN DEL TEST ===" -ForegroundColor Cyan
