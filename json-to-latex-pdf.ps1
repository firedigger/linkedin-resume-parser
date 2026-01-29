param(
    [string]$Resume = "resume.json",
    [string]$Template = "template.tex",
    [string]$TexOut = "resume.tex"
)

if (-not (Get-Command pdflatex -ErrorAction SilentlyContinue)) {
    throw "pdflatex not found. Install MiKTeX or TeX Live and ensure it is on PATH."
}

python -m linkedin_resume_parser.latex $Resume -t $Template -o $TexOut
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$outputDir = Split-Path -Parent $TexOut
if (-not $outputDir) {
    $outputDir = "."
}

pdflatex -interaction=nonstopmode -halt-on-error -output-directory $outputDir $TexOut 2>&1 | Out-Null
exit $LASTEXITCODE
