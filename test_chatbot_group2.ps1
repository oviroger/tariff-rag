# TEST GRUPO 2: ALIMENTOS Y BEBIDAS
# Simulación de conversación: el chatbot sugiere preguntas, el usuario responde parcialmente

$Years = @("2026")
$OutputFile = "test_chatbot_group2_resultados.txt"

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
            "cheese" {
                if ($f -match "tipo|fresco|madurado|pasta") { $answers += "Queso madurado"; continue }
                if ($f -match "leche|vaca|oveja|cabra") { $answers += "Leche de vaca"; continue }
                if ($f -match "grasa|contenido graso") { $answers += "45% materia grasa"; continue }
                if ($f -match "rallado|tajado|bloque") { $answers += "En bloque"; continue }
            }
            "wine" {
                if ($f -match "tipo|tinto|blanco|rose|espumoso") { $answers += "Vino tinto"; continue }
                if ($f -match "graduacion|alcohol|grados") { $answers += "13.5 grados"; continue }
                if ($f -match "origen|pais|denominacion") { $answers += "Origen Chile"; continue }
                if ($f -match "envase|botella|litros") { $answers += "Botella 750 ml"; continue }
            }
            "chocolate" {
                if ($f -match "cacao|porcentaje|contenido") { $answers += "70% cacao"; continue }
                if ($f -match "leche|negro|blanco") { $answers += "Chocolate negro"; continue }
                if ($f -match "relleno|sin relleno") { $answers += "Sin relleno"; continue }
                if ($f -match "presentacion|barra|tableta|polvo") { $answers += "En tableta"; continue }
            }
            "juice" {
                if ($f -match "fruta|naranja|manzana|uva") { $answers += "Jugo de naranja"; continue }
                if ($f -match "concentrado|natural|reconstituido") { $answers += "Natural"; continue }
                if ($f -match "azucar|edulcorante|endulzado") { $answers += "Sin azúcar añadida"; continue }
                if ($f -match "envase|litro|ml") { $answers += "Envase 1 litro"; continue }
            }
            "fish" {
                if ($f -match "tipo|salmon|atun|merluza|pescado") { $answers += "Salmón"; continue }
                if ($f -match "fresco|congelado|conserva") { $answers += "Congelado"; continue }
                if ($f -match "filete|entero|trozo") { $answers += "En filetes"; continue }
                if ($f -match "procesamiento|ahumado|salado") { $answers += "Sin procesar"; continue }
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

# Escenarios: Alimentos y bebidas ambiguos
$scenarios = @(
    @{ name = "Queso"; query = "Queso"; type = "cheese" },
    @{ name = "Vino"; query = "Vino"; type = "wine" },
    @{ name = "Chocolate"; query = "Chocolate"; type = "chocolate" },
    @{ name = "Jugo"; query = "Jugo de fruta"; type = "juice" },
    @{ name = "Pescado"; query = "Pescado"; type = "fish" }
)

$fullOutput = "=== TEST CHATBOT CON RESPUESTAS PARCIALES - GRUPO 2: ALIMENTOS Y BEBIDAS ===`n"

foreach ($sc in $scenarios) {
    Write-Host "Ejecutando test: $($sc.name)..." -ForegroundColor Cyan
    $fullOutput += Simulate-Conversation $sc.name $sc.query $sc.type $Years 4
}

$fullOutput += "`n✅ Test finalizado"

# Guardar resultados
$fullOutput | Out-File -FilePath $OutputFile -Encoding UTF8
Write-Host "`n✅ Resultados guardados en: $OutputFile" -ForegroundColor Green
Write-Host $fullOutput
