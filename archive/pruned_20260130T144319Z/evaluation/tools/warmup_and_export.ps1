param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$Endpoint = "/classify",
  [string]$Method = "POST",
  [int]$Health = 20,
  [int]$Classify = 20,
  [int]$Workers = 5,
  [string]$Query = "Necesito importar plátanos",
  [string]$Output = "evaluation/templates/logs_operativos.csv"
)

$ErrorActionPreference = "Stop"

# Resolve repo root relative to this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../..")
$Warmup = Join-Path $RepoRoot "evaluation/tools/warmup_requests.py"
$Exporter = Join-Path $RepoRoot "evaluation/export_logs_operativos.py"

Write-Host "[1/2] Generando tráfico ($Health health, $Classify classify) en $BaseUrl ..."
python "$Warmup" --base-url $BaseUrl --health $Health --classify $Classify --workers $Workers --query "$Query"

# Build metrics URL
if ($BaseUrl.EndsWith('/')) { $BaseUrl = $BaseUrl.TrimEnd('/') }
$MetricsUrl = "$BaseUrl/metrics"

Write-Host "[2/2] Exportando métricas desde $MetricsUrl a $Output (endpoint=$Endpoint, method=$Method) ..."
python "$Exporter" --url $MetricsUrl --endpoint $Endpoint --method $Method --output "$Output"

Write-Host "Completado. Revisa $Output"
