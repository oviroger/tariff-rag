# Simulación de conversación: el chatbot sugiere preguntas, el usuario responde parcialmente
# Verifica coherencia API vs UI (Gradio chat_minimal_validation)

$Years = @("2026")

function Invoke-Api($message, $history, $years) {
    $payload = @{ user_query = $message; conversation_history = $history; years = $years } | ConvertTo-Json -Depth 6
    $resp = Invoke-WebRequest -Uri "http://localhost:8000/classify" -Method Post -ContentType "application/json" -Body $payload -ErrorAction Stop
    return ($resp.Content | ConvertFrom-Json)
}

function Get-UIResponse($message, $history, $convId, $years, $session) {
    $joinBody = @{ data = @($message, $history, $convId, $years); fn_index = 7; session_hash = $session } | ConvertTo-Json -Depth 6
    $joinResp = Invoke-WebRequest -Uri "http://localhost:7860/gradio_api/queue/join" -Method Post -ContentType "application/json" -Body $joinBody -ErrorAction Stop
    $eventId = ($joinResp.Content | ConvertFrom-Json).event_id

    $queueUrl = "http://localhost:7860/gradio_api/queue/data?session_hash=$session"
    $queueResp = Invoke-WebRequest -Uri $queueUrl -Method Get -ErrorAction Stop

    $lines = $queueResp.Content -split "`n"
    $completedLine = $lines | Where-Object { $_ -match '"process_completed"' } | Select-Object -First 1
    if (-not $completedLine) { return @{ response = $null; conv_id = $convId } }

    $json = $completedLine.Replace("data: ", "") | ConvertFrom-Json
    $responseText = $json.output.data[0]
    $newConvId = $json.output.data[1]
    return @{ response = $responseText; conv_id = $newConvId }
}

function Extract-CodeFromMarkdown($markdown) {
    if (-not $markdown) { return "N/A" }
    $match = [regex]::Match($markdown, "\*\*a\)\s*([0-9\.]+)\*\*", "IgnoreCase")
    if ($match.Success) { return $match.Groups[1].Value }
    # Fallback: primer patrón de código (evitar 9999.00 si hay otro)
    $fallback = [regex]::Matches($markdown, "\b\d{4}\.\d{2}(?:\.\d{2})?(?:\.\d{2})?\b")
    if ($fallback.Count -gt 0) {
        $first = $fallback[0].Value
        if ($first -ne "9999.00") { return $first }
        if ($fallback.Count -gt 1) { return $fallback[1].Value }
        return $first
    }
    return "N/A"
}

function Extract-QuestionsFromMarkdown($markdown) {
    if (-not $markdown) { return @() }
    $lines = $markdown -split "`n"
    $questions = @()
    $capture = $false
    foreach ($line in $lines) {
        if ($line -match "Información adicional") { $capture = $true; continue }
        if ($capture -and $line -match "^---") { break }
        if ($capture -and $line.Trim().StartsWith("-")) {
            $q = $line.Trim().TrimStart("-").Trim()
            if ($q) { $questions += $q }
        }
    }
    return $questions
}

function Build-PartialAnswer($missingFields, $usedAnswers, $productType) {
    if (-not $missingFields -or $missingFields.Count -eq 0) { return $null }

    # Responder solo 1-2 preguntas por turno (parcial)
    $answers = @()
    foreach ($field in $missingFields) {
        $f = $field.ToLowerInvariant()

        switch ($productType) {
            "steel" {
                if ($f -match "espesor|grosor|mm") { $answers += "Espesor 2 mm"; continue }
                if ($f -match "galvanizado|recubrimiento|pintado") { $answers += "Sin recubrimiento"; continue }
                if ($f -match "acabado|laminado") { $answers += "Laminado en caliente"; continue }
                if ($f -match "composicion|inoxidable|carbono") { $answers += "Acero al carbono"; continue }
            }
            "washer" {
                if ($f -match "capacidad|kg") { $answers += "Capacidad 9 kg"; continue }
                if ($f -match "carga frontal|superior") { $answers += "Carga frontal"; continue }
                if ($f -match "voltaje|v") { $answers += "220 V"; continue }
                if ($f -match "domestic|domestico|hogar") { $answers += "Uso doméstico"; continue }
                if ($f -match "nuevo|usado") { $answers += "Nuevo"; continue }
            }
            "microwave" {
                if ($f -match "capacidad" -and $f -match "litro|l") { $answers += "Capacidad 30 L"; continue }
                if ($f -match "grill|conveccion") { $answers += "Con grill"; continue }
                if ($f -match "potencia|w") { $answers += "1200 W"; continue }
                if ($f -match "nuevo|usado") { $answers += "Nuevo"; continue }
            }
            "truck" {
                if ($f -match "motor|diesel|di[eí]sel") { $answers += "Motor diésel"; continue }
                if ($f -match "cilindrada|cc|cm3") { $answers += "Cilindrada 3000 cc"; continue }
                if ($f -match "plazas|personas|pasajeros") { $answers += "Capacidad 2 personas"; continue }
                if ($f -match "nuevo|usado") { $answers += "Nuevo"; continue }
            }
            "textile" {
                if ($f -match "material|algodon|poliester|lana") { $answers += "100% algodón"; continue }
                if ($f -match "tejido|punto|no tejido") { $answers += "Tejido de punto"; continue }
                if ($f -match "uso final|prenda|vestimenta") { $answers += "Uso vestimenta"; continue }
                if ($f -match "tipo especifico|tipo de camiseta|camiseta") { $answers += "Camiseta de algodón"; continue }
            }
            "laptop" {
                if ($f -match "pantalla|pulgadas|tamaño") { $answers += "Pantalla 15 pulgadas"; continue }
                if ($f -match "procesador|cpu") { $answers += "Procesador Intel Core i7"; continue }
                if ($f -match "ram|memoria") { $answers += "16 GB RAM"; continue }
                if ($f -match "sistema operativo|os|windows|linux") { $answers += "Windows 11"; continue }
                if ($f -match "nuevo|usado") { $answers += "Nuevo"; continue }
            }
            "shoes" {
                if ($f -match "material|cuero|sintetico|textil") { $answers += "Cuero natural"; continue }
                if ($f -match "suela|piso") { $answers += "Suela de caucho"; continue }
                if ($f -match "tipo|uso|deporte|formal") { $answers += "Zapatos casuales"; continue }
                if ($f -match "genero|hombre|mujer|niño") { $answers += "Para hombre"; continue }
                if ($f -match "nuevo|usado") { $answers += "Nuevo"; continue }
            }
            "coffee" {
                if ($f -match "tostado|crudo|verde") { $answers += "Café tostado"; continue }
                if ($f -match "descafeinado|cafeina") { $answers += "Con cafeína"; continue }
                if ($f -match "molido|grano") { $answers += "En grano"; continue }
                if ($f -match "origen|pais") { $answers += "Origen Colombia"; continue }
                if ($f -match "empaque|envase") { $answers += "Empaque al vacío"; continue }
            }
            "furniture" {
                if ($f -match "material|madera|metal|plastico") { $answers += "Madera maciza"; continue }
                if ($f -match "tipo|mesa|silla|estante") { $answers += "Mesa de comedor"; continue }
                if ($f -match "dimensiones|tamaño|medidas") { $answers += "2 metros de largo"; continue }
                if ($f -match "acabado|barniz|pintura") { $answers += "Acabado en barniz"; continue }
                if ($f -match "uso|domestico|oficina") { $answers += "Uso doméstico"; continue }
            }
            "toy" {
                if ($f -match "material|plastico|madera|textil") { $answers += "Plástico ABS"; continue }
                if ($f -match "edad|años|niños") { $answers += "Para niños de 3-6 años"; continue }
                if ($f -match "tipo|muñeca|carro|peluche") { $answers += "Carro de juguete"; continue }
                if ($f -match "electronico|pilas|baterias") { $answers += "No electrónico"; continue }
                if ($f -match "dimensiones|tamaño") { $answers += "Tamaño 20 cm"; continue }
            }
            "valve" {
                if ($f -match "material|acero|bronce|hierro|plastico") { $answers += "Material bronce"; continue }
                if ($f -match "uso|aplicacion|agua|gas|vapor|aire") { $answers += "Para agua"; continue }
                if ($f -match "diametro|tamaño|pulgadas|mm") { $answers += "Diámetro 2 pulgadas"; continue }
                if ($f -match "presion|bar|psi") { $answers += "Presión 10 bar"; continue }
                if ($f -match "tipo|compuerta|bola|globo|retencion") { $answers += "Válvula de bola"; continue }
            }
            "tube" {
                if ($f -match "material|acero|cobre|plastico|pvc") { $answers += "Acero inoxidable"; continue }
                if ($f -match "diametro|calibre|espesor") { $answers += "Diámetro 50 mm"; continue }
                if ($f -match "uso|conduccion|estructural|mecanico") { $answers += "Uso en conducción de fluidos"; continue }
                if ($f -match "largo|longitud|metros") { $answers += "Longitud 6 metros"; continue }
                if ($f -match "soldado|sin costura") { $answers += "Sin costura"; continue }
            }
            "pump" {
                if ($f -match "tipo|centrifuga|desplazamiento|sumergible") { $answers += "Bomba centrífuga"; continue }
                if ($f -match "fluido|agua|aceite|quimicos") { $answers += "Para agua"; continue }
                if ($f -match "potencia|hp|kw") { $answers += "Potencia 5 HP"; continue }
                if ($f -match "caudal|litros|m3") { $answers += "Caudal 100 L/min"; continue }
                if ($f -match "uso|industrial|domestico|agricola") { $answers += "Uso industrial"; continue }
            }
            "motor" {
                if ($f -match "potencia|hp|kw|watts") { $answers += "Potencia 2 HP"; continue }
                if ($f -match "voltaje|v|tension") { $answers += "220V trifásico"; continue }
                if ($f -match "rpm|velocidad|revoluciones") { $answers += "1500 RPM"; continue }
                if ($f -match "uso|industrial|domestico") { $answers += "Uso industrial"; continue }
                if ($f -match "tipo|asincrono|sincrono") { $answers += "Motor asíncrono"; continue }
            }
            "oil" {
                if ($f -match "tipo|mineral|sintetico|vegetal|animal") { $answers += "Aceite mineral"; continue }
                if ($f -match "uso|motor|lubricante|hidraulico|comestible") { $answers += "Lubricante industrial"; continue }
                if ($f -match "viscosidad|sae|iso") { $answers += "Viscosidad SAE 40"; continue }
                if ($f -match "origen|petroleo|vegetal|sintetico") { $answers += "Derivado del petróleo"; continue }
                if ($f -match "grado|calidad|aditivos") { $answers += "Con aditivos"; continue }
            }
        }
    }

    # Tomar solo 2 respuestas máximo, evitando repetir respuestas previas y duplicados
    $filtered = @()
    foreach ($a in $answers) {
        if (-not ($usedAnswers -contains $a) -and -not ($filtered -contains $a)) {
            $filtered += $a
        }
    }
    $selected = $filtered | Select-Object -First 2
    if (-not $selected -or $selected.Count -eq 0) { return $null }
    return ($selected -join ". ")
}

function Simulate-Conversation($title, $initialQuery, $productType, $years, $maxTurns = 4) {
    Write-Host "\n=== $title ===" -ForegroundColor Cyan
    $apiHistory = @()
    $userMessages = @($initialQuery)
    $usedAnswers = @()

    $currentQuery = $initialQuery
    for ($turn = 1; $turn -le $maxTurns; $turn++) {
        $result = Invoke-Api $currentQuery $apiHistory $years
        $code = if ($result.top_candidates.Count -gt 0) { $result.top_candidates[0].code } else { "N/A" }
        $conf = if ($result.top_candidates.Count -gt 0) { [Math]::Round($result.top_candidates[0].confidence * 100, 2) } else { 0 }
        $missing = $result.missing_fields

        Write-Host "Turno $turn | Query: $currentQuery" -ForegroundColor Yellow
        Write-Host "API -> $code ($conf%) | Missing: $($missing.Count)"
        if ($missing -and $missing.Count -gt 0) {
            Write-Host "Opciones sugeridas por el chatbot:" -ForegroundColor Cyan
            $missing | ForEach-Object { Write-Host " - $_" }
        }

        # Guardar en historial
        $apiHistory += @{ user = $currentQuery; assistant = "Código: $code" }

        if (-not $missing -or $missing.Count -eq 0) { break }

        $partialAnswer = Build-PartialAnswer $missing $usedAnswers $productType
        if (-not $partialAnswer -or $partialAnswer.Trim() -eq "") { break }

        Write-Host "Respuesta parcial del usuario:" -ForegroundColor Green
        Write-Host " - $partialAnswer"

        $currentQuery = $partialAnswer
        $usedAnswers += ($partialAnswer -split "\. ")
        $userMessages += $currentQuery
    }

    # Simular mismo flujo en UI
    $convId = ""
    $uiHistory = @()
    $uiCodeFinal = "N/A"
    $uiSession = [guid]::NewGuid().ToString("N")

    $uiMessage = $initialQuery
    $usedAnswersUi = @()

    $turn = 1
    while ($turn -le $maxTurns) {
        # Usar historial acumulado en formato Gradio [(user, assistant), ...]
        $uiResult = Get-UIResponse $uiMessage $uiHistory $convId $years $uiSession
        $uiMarkdown = $uiResult.response
        $convId = if ($uiResult.conv_id) { $uiResult.conv_id } else { $convId }

        $uiCode = Extract-CodeFromMarkdown $uiMarkdown
        if ($uiCode -ne "N/A") { $uiCodeFinal = $uiCode }

        $uiHistory += @(@($uiMessage, $uiMarkdown))
        Write-Host "UI Turno $turn -> $uiCode" -ForegroundColor DarkGray
        if ($uiMarkdown) {
            $preview = $uiMarkdown -replace "\r", "" -replace "\n", " "
            if ($preview.Length -gt 160) { $preview = $preview.Substring(0,160) + "..." }
            Write-Host "UI respuesta: $preview" -ForegroundColor DarkGray
        }
        $uiQuestions = Extract-QuestionsFromMarkdown $uiMarkdown
        if (-not $uiQuestions -or $uiQuestions.Count -eq 0) { break }

        $uiAnswer = Build-PartialAnswer $uiQuestions $usedAnswersUi $productType
        if (-not $uiAnswer) { break }

        Write-Host "UI opciones sugeridas:" -ForegroundColor DarkGray
        $uiQuestions | ForEach-Object { Write-Host " - $_" -ForegroundColor DarkGray }
        Write-Host "UI respuesta parcial del usuario:" -ForegroundColor DarkGray
        Write-Host " - $uiAnswer" -ForegroundColor DarkGray

        $usedAnswersUi += ($uiAnswer -split "\. ")
        $uiMessage = $uiAnswer
        $turn++
    }

    Write-Host "UI -> Código final: $uiCodeFinal" -ForegroundColor Green
    return @{ api_messages = $userMessages; ui_code = $uiCodeFinal }
}

# Escenarios: productos ambiguos que requieren múltiples turnos de refinamiento
$scenarios = @(
    @{ name = "Válvula"; query = "Válvula"; type = "valve" },
    @{ name = "Tubo"; query = "Tubo"; type = "tube" },
    @{ name = "Bomba"; query = "Bomba"; type = "pump" },
    @{ name = "Motor"; query = "Motor eléctrico"; type = "motor" },
    @{ name = "Aceite"; query = "Aceite"; type = "oil" }
)

Write-Host "=== TEST CHATBOT CON RESPUESTAS PARCIALES ===" -ForegroundColor Magenta

foreach ($sc in $scenarios) {
    Simulate-Conversation $sc.name $sc.query $sc.type $Years 4 | Out-Null
}

Write-Host "\n✅ Test finalizado" -ForegroundColor Green
