# =============================================================================
#  PyAutoFlow — PowerShell Script Wrapper (Windows)
#  Convenience script for running common pipeline workflows on Windows.
# =============================================================================

param(
    [string]$Command = "help"
)

$PYTHON = if ($env:PYTHON) { $env:PYTHON } else { "python" }

function Write-Info    { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Cyan    }
function Write-Success { param($msg) Write-Host "[OK]    $msg" -ForegroundColor Green   }
function Write-Warn    { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow  }

function Show-Usage {
    Write-Host @"
PyAutoFlow PowerShell Wrapper

Usage: .\run.ps1 <command>

Commands:
  csv       Process the sample CSV file
  json      Process the sample JSON file
  api       Fetch live data from the demo REST API
  test      Run all unit tests with pytest
  full      Full demo: CSV + group aggregation + all report formats
  help      Show this message
"@ -ForegroundColor White
}

function Invoke-Csv {
    Write-Info "Running CSV pipeline..."
    & $PYTHON -m pyautoflow.cli `
        --input data/sample_input.csv `
        --group-by region category `
        --agg revenue:sum units:mean `
        --outlier-col revenue `
        --formats csv json txt
    Write-Success "CSV pipeline complete. Reports in output/"
}

function Invoke-Json {
    Write-Info "Running JSON pipeline..."
    & $PYTHON -m pyautoflow.cli `
        --input data/sample_input.json `
        --group-by region `
        --agg revenue:sum units:sum `
        --formats csv json txt
    Write-Success "JSON pipeline complete. Reports in output/"
}

function Invoke-Api {
    Write-Info "Fetching live data from API..."
    & $PYTHON -m pyautoflow.cli `
        --source api `
        --api-endpoint posts `
        --api-limit 50 `
        --formats csv txt
    Write-Success "API pipeline complete. Reports in output/"
}

function Invoke-Tests {
    Write-Info "Running test suite..."
    & $PYTHON -m pytest tests/ -v --tb=short --cov=pyautoflow --cov-report=term-missing
    Write-Success "All tests passed."
}

function Invoke-Full {
    Write-Info "Running full demo pipeline..."
    & $PYTHON -m pyautoflow.cli `
        --input data/sample_input.csv `
        --filter "units > 5" "revenue > 0" `
        --derive "profit=revenue - cost" "margin_pct=profit / revenue * 100" `
        --group-by region category `
        --agg revenue:sum cost:sum units:mean `
        --rolling-col revenue `
        --rolling-window 5 `
        --outlier-col revenue `
        --outlier-multiplier 1.5 `
        --formats csv json txt `
        --label demo_run
    Write-Success "Full demo complete. Reports in output/"
}

switch ($Command.ToLower()) {
    "csv"  { Invoke-Csv   }
    "json" { Invoke-Json  }
    "api"  { Invoke-Api   }
    "test" { Invoke-Tests }
    "full" { Invoke-Full  }
    "help" { Show-Usage   }
    default {
        Write-Warn "Unknown command: '$Command'"
        Show-Usage
        exit 1
    }
}
