# TEST GRUPO 5: ELECTRÓNICA Y ELECTRODOMÉSTICOS
# Simulación de conversación: el chatbot sugiere preguntas, el usuario responde parcialmente

$Years = @("2026")
$OutputFile = "test_chatbot_group5_resultados.txt"

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
    $fallback = [regex]::Matches($markdown, "\b\d{4}\.\d{2}(?:\.\d{2})?(?:\.\d{2})?\b")
    if ($fallback.Count -gt 0) {
        $first = $fallback[0].Value
        if ($first -ne "9999.00") { return $first }
        if ($fallback.Count -gt 1) { return $fallback[1].Value }
        return $first
    }
    return "N/A"
}

function Extract-Questions($markdown) {
    if (-not $markdown) { return @() }
    $section = if ($markdown -match "(?s)Información adicional sugerida(.*?)(?:---|\z)") { $Matches[1] } else { "" }
    $questions = [regex]::Matches($section, "- (.+?)(?=\n-|\z)", "Singleline") | ForEach-Object { $_.Groups[1].Value.Trim() }
    return $questions
}

function Build-PartialAnswer($missingFields, $usedAnswers, $productType) {
    if (-not $missingFields -or $missingFields.Count -eq 0) { return $null }

    $answers = @()
    foreach ($field in $missingFields) {
        $f = $field.ToLowerInvariant()

        switch ($productType) {
            "tv" {
                if ($f -match "pantalla|pulgadas|tamaño") { $answers += "Pantalla 55 pulgadas"; continue }
                if ($f -match "tipo|lcd|led|oled|plasma") { $answers += "LED"; continue }
                if ($f -match "resolucion|4k|hd|full hd") { $answers += "Resolución 4K"; continue }
                if ($f -match "smart|inteligente|internet") { $answers += "Smart TV"; continue }
            }
            "speaker" {
                if ($f -match "tipo|activo|pasivo|bluetooth") { $answers += "Parlante Bluetooth"; continue }
                if ($f -match "potencia|watts|w") { $answers += "Potencia 20W"; continue }
                if ($f -match "uso|portatil|fijo|profesional") { $answers += "Portátil"; continue }
                if ($f -match "canales|estereo|mono") { $answers += "Estéreo"; continue }
            }
            "printer" {
                if ($f -match "tipo|laser|inyeccion|multifuncion") { $answers += "Inyección de tinta"; continue }
                if ($f -match "color|blanco negro|monocromatica") { $answers += "A color"; continue }
                if ($f -match "uso|domestico|oficina|industrial") { $answers += "Uso doméstico"; continue }
                if ($f -match "funciones|imprime|escanea|copia") { $answers += "Imprime y escanea"; continue }
            }
            "fan" {
                if ($f -match "tipo|mesa|piso|techo|torre") { $answers += "Ventilador de piso"; continue }
                if ($f -match "diametro|aspas|pulgadas") { $answers += "Aspas 18 pulgadas"; continue }
                if ($f -match "velocidades|ajustes") { $answers += "3 velocidades"; continue }
                if ($f -match "uso|domestico|industrial") { $answers += "Uso doméstico"; continue }
            }
            "heater" {
                if ($f -match "tipo|electrico|gas|infrarrojo") { $answers += "Calefactor eléctrico"; continue }
                if ($f -match "potencia|watts|w") { $answers += "Potencia 1500W"; continue }
                if ($f -match "uso|ambiente|agua|industrial") { $answers += "Calefacción de ambiente"; continue }
                if ($f -match "portabilidad|portatil|fijo") { $answers += "Portátil"; continue }
            }
        }
    }

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
    $output = "`n=== $title ===`n"
    $apiHistory = @()
    $userMessages = @($initialQuery)
    $usedAnswers = @()

    $currentQuery = $initialQuery
    for ($turn = 1; $turn -le $maxTurns; $turn++) {
        $result = Invoke-Api $currentQuery $apiHistory $years
        $code = if ($result.top_candidates.Count -gt 0) { $result.top_candidates[0].code } else { "N/A" }
        $conf = if ($result.top_candidates.Count -gt 0) { [Math]::Round($result.top_candidates[0].confidence * 100, 2) } else { 0 }
        $missing = $result.missing_fields

        $output += "Turno $turn | Query: $currentQuery`n"
        $output += "API -> $code ($conf%) | Missing: $($missing.Count)`n"
        if ($missing -and $missing.Count -gt 0) {
            $output += "Opciones sugeridas por el chatbot:`n"
            $missing | ForEach-Object { $output += " - $_`n" }
        }

        $apiHistory += @{ user = $currentQuery; assistant = "Código: $code" }

        if (-not $missing -or $missing.Count -eq 0) { break }

        $partialAnswer = Build-PartialAnswer $missing $usedAnswers $productType
        if (-not $partialAnswer -or $partialAnswer.Trim() -eq "") { break }

        $output += "Respuesta parcial del usuario:`n"
        $output += " - $partialAnswer`n"

        $currentQuery = $partialAnswer
        $usedAnswers += ($partialAnswer -split "\. ")
        $userMessages += $currentQuery
    }

    $convId = ""
    $uiHistory = @()
    $uiCodeFinal = "N/A"
    $uiSession = [guid]::NewGuid().ToString("N")

    $uiMessage = $initialQuery
    $usedAnswersUi = @()
    $turn = 1

    while ($turn -le $maxTurns) {
        $uiResp = Get-UIResponse $uiMessage $uiHistory $convId $years $uiSession
        $uiText = $uiResp.response
        $convId = $uiResp.conv_id

        $uiCode = Extract-CodeFromMarkdown $uiText
        $uiCodeFinal = $uiCode
        $uiQuestions = Extract-Questions $uiText

        $output += "UI Turno $turn -> $uiCode`n"
        $output += "UI respuesta: $($uiText.Substring(0, [Math]::Min(150, $uiText.Length)))...`n"

        $uiHistory += @($uiMessage, $uiText)

        if (-not $uiQuestions -or $uiQuestions.Count -eq 0) { break }

        $uiAnswer = Build-PartialAnswer $uiQuestions $usedAnswersUi $productType
        if (-not $uiAnswer) { break }

        $output += "UI opciones sugeridas:`n"
        $uiQuestions | ForEach-Object { $output += " - $_`n" }
        $output += "UI respuesta parcial del usuario:`n"
        $output += " - $uiAnswer`n"

        $usedAnswersUi += ($uiAnswer -split "\. ")
        $uiMessage = $uiAnswer
        $turn++
    }

    $output += "UI -> Código final: $uiCodeFinal`n"
    return $output
}

# Escenarios: Electrónica y electrodomésticos ambiguos
$scenarios = @(
    @{ name = "Televisor"; query = "Televisor"; type = "tv" },
    @{ name = "Parlante"; query = "Parlante"; type = "speaker" },
    @{ name = "Impresora"; query = "Impresora"; type = "printer" },
    @{ name = "Ventilador"; query = "Ventilador"; type = "fan" },
    @{ name = "Calefactor"; query = "Calefactor"; type = "heater" }
)

$fullOutput = "=== TEST CHATBOT CON RESPUESTAS PARCIALES - GRUPO 5: ELECTRÓNICA Y ELECTRODOMÉSTICOS ===`n"

foreach ($sc in $scenarios) {
    Write-Host "Ejecutando test: $($sc.name)..." -ForegroundColor Cyan
    $fullOutput += Simulate-Conversation $sc.name $sc.query $sc.type $Years 4
}

$fullOutput += "`n✅ Test finalizado"

# Guardar resultados
$fullOutput | Out-File -FilePath $OutputFile -Encoding UTF8
Write-Host "`n✅ Resultados guardados en: $OutputFile" -ForegroundColor Green
Write-Host $fullOutput
