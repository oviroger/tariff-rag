# EJECUTAR TODOS LOS GRUPOS DE TESTS
# Este script ejecuta secuencialmente todos los grupos de productos

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST COMPLETO - CLASIFICACIÓN ARANCELARIA MULTI-TURNO      ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$grupos = @(
    @{ nombre = "GRUPO 2: ALIMENTOS Y BEBIDAS"; script = "test_chatbot_group2.ps1"; color = "Green" },
    @{ nombre = "GRUPO 3: TEXTILES Y CALZADO"; script = "test_chatbot_group3.ps1"; color = "Yellow" },
    @{ nombre = "GRUPO 4: QUÍMICOS Y FARMACÉUTICOS"; script = "test_chatbot_group4.ps1"; color = "Magenta" },
    @{ nombre = "GRUPO 5: ELECTRÓNICA Y ELECTRODOMÉSTICOS"; script = "test_chatbot_group5.ps1"; color = "Cyan" }
)

$startTime = Get-Date

foreach ($grupo in $grupos) {
    Write-Host "`n" -NoNewline
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor $grupo.color
    Write-Host "  $($grupo.nombre)" -ForegroundColor $grupo.color
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor $grupo.color
    Write-Host ""
    
    try {
        & pwsh -ExecutionPolicy Bypass -File $grupo.script
        Write-Host "`n✅ $($grupo.nombre) completado`n" -ForegroundColor Green
    } catch {
        Write-Host "`n❌ Error en $($grupo.nombre): $_`n" -ForegroundColor Red
    }
    
    # Pausa entre grupos para evitar sobrecarga
    Start-Sleep -Seconds 5
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TESTS COMPLETADOS                                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host "Tiempo total: $($duration.TotalMinutes.ToString('F2')) minutos" -ForegroundColor Yellow
Write-Host ""
Write-Host "Archivos de resultados generados:" -ForegroundColor White
Write-Host "  - test_chatbot_group1_resultados.txt (ya ejecutado)" -ForegroundColor Gray
Write-Host "  - test_chatbot_group2_resultados.txt" -ForegroundColor Gray
Write-Host "  - test_chatbot_group3_resultados.txt" -ForegroundColor Gray
Write-Host "  - test_chatbot_group4_resultados.txt" -ForegroundColor Gray
Write-Host "  - test_chatbot_group5_resultados.txt" -ForegroundColor Gray
Write-Host ""
