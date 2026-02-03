param(
    [string]$Resume = "resume.json",
    [string]$Template = "template.tex",
    [string]$TexOut = "resume.tex",
    [switch]$Basic,
    [switch]$Latinize,
    [switch]$ForcePdfLatex,
    [switch]$Dark
)

$latexArgs = @()
$templatePath = $Template
$forcePdfLatexLocal = $ForcePdfLatex
if ($Basic) {
    $latexArgs += "--basic"
    if ($Template -eq "template.tex") {
        $templatePath = "template_basic.tex"
    }
    if ($TexOut -eq "resume.tex") {
        $TexOut = "resume_basic.tex"
    }
}

if ($Latinize) {
    $latexArgs += "--latinize"
    $forcePdfLatexLocal = $true
}

if ($Dark) {
    $latexArgs += "--dark"
}

python -m linkedin_resume_parser.latex $Resume -t $templatePath -o $TexOut @latexArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$outputDir = Split-Path -Parent $TexOut
if (-not $outputDir) {
    $outputDir = "."
}

$pdfName = [IO.Path]::GetFileNameWithoutExtension($TexOut) + ".pdf"
$pdfPath = Join-Path $outputDir $pdfName

$texContent = Get-Content -Path $TexOut -Raw -Encoding UTF8
$hasNonAscii = $texContent -match '[^\u0000-\u007F]'

if ($forcePdfLatexLocal -and -not $Latinize -and $hasNonAscii) {
    throw "Non-ASCII content detected. Use -Latinize or allow Unicode engine switching."
}

$engine = "pdflatex"
if (-not $forcePdfLatexLocal -and $hasNonAscii) {
    if (Get-Command xelatex -ErrorAction SilentlyContinue) {
        $engine = "xelatex"
    } elseif (Get-Command lualatex -ErrorAction SilentlyContinue) {
        $engine = "lualatex"
    } else {
        throw "xelatex or lualatex not found. Install MiKTeX or TeX Live with Unicode support and ensure it is on PATH."
    }
}

if ($engine -eq "pdflatex" -and -not (Get-Command pdflatex -ErrorAction SilentlyContinue)) {
    throw "pdflatex not found. Install MiKTeX or TeX Live and ensure it is on PATH."
}

$logPath = Join-Path $outputDir ([IO.Path]::GetFileNameWithoutExtension($TexOut) + ".${engine}.log")

& $engine -interaction=nonstopmode -halt-on-error -output-directory $outputDir $TexOut *> $logPath
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0 -or -not (Test-Path $pdfPath)) {
    Write-Error "$engine failed or PDF not produced. Exit code: $exitCode"
    Write-Error "See log: $logPath"
    if (Test-Path $logPath) {
        Write-Output "Last 40 lines of $engine log:"
        Get-Content $logPath -Tail 40
    }
    exit 1
}

exit 0
