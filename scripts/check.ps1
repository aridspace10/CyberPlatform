Write-Host "=== BLACK ==="
python -m black --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== RUFF ==="
python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Uncomment later
# Write-Host "=== MYPY ==="
# python -m mypy .
# if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "All checks passed."