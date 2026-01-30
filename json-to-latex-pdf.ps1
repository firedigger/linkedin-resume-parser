param(
    [string]$Resume = "resume.json",
    [string]$Template = "template.tex",
    [string]$TexOut = "resume.tex",
    [switch]$Basic
)

if (-not (Get-Command pdflatex -ErrorAction SilentlyContinue)) {
    throw "pdflatex not found. Install MiKTeX or TeX Live and ensure it is on PATH."
}

$basicArgs = @()
$templatePath = $Template
if ($Basic) {
    $basicArgs = @("--basic")
    if ($Template -eq "template.tex") {
        $templatePath = "template_basic.tex"
    }
    if ($TexOut -eq "resume.tex") {
        $TexOut = "resume_basic.tex"
    }
}

python -m linkedin_resume_parser.latex $Resume -t $templatePath -o $TexOut @basicArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$outputDir = Split-Path -Parent $TexOut
if (-not $outputDir) {
    $outputDir = "."
}

$pdfName = [IO.Path]::GetFileNameWithoutExtension($TexOut) + ".pdf"
$pdfPath = Join-Path $outputDir $pdfName
$logPath = Join-Path $outputDir ([IO.Path]::GetFileNameWithoutExtension($TexOut) + ".pdflatex.log")

pdflatex -interaction=nonstopmode -halt-on-error -output-directory $outputDir $TexOut *> $logPath
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0 -or -not (Test-Path $pdfPath)) {
    Write-Error "pdflatex failed or PDF not produced. Exit code: $exitCode"
    Write-Error "See log: $logPath"
    if (Test-Path $logPath) {
        Write-Output "Last 40 lines of pdflatex log:"
        Get-Content $logPath -Tail 40
    }
    exit 1
}

exit 0
