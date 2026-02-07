param(
    [Parameter(Mandatory = $true)]
    [string]$LinkedInPdf,
    [string]$ResumeJson,
    [string]$PersonalInfo = "personal_info.json",
    [string]$SkillsCsv = "Skills.csv",
    [string]$CertificationsCsv = "Certifications.csv",
    [string]$ProjectsCsv = "Projects.csv",
    [string]$Template = "template.tex",
    [string]$TexOut,
    [string]$EuropassXml,
    [string]$EuropassConfig = "europass_config.json",
    [switch]$SkipEuropass,
    [switch]$Basic,
    [switch]$Latinize,
    [switch]$ForcePdfLatex,
    [switch]$Dark
)

if (-not (Test-Path $LinkedInPdf)) {
    throw "LinkedIn PDF not found: $LinkedInPdf"
}

$baseName = [IO.Path]::GetFileNameWithoutExtension($LinkedInPdf)
if ([string]::IsNullOrWhiteSpace($ResumeJson)) {
    $ResumeJson = "${baseName}_resume.json"
}
if ([string]::IsNullOrWhiteSpace($TexOut)) {
    $TexOut = "${baseName}_SWE.tex"
}
if ([string]::IsNullOrWhiteSpace($EuropassXml)) {
    $EuropassXml = "${baseName}_europass.xml"
}

python -m linkedin_resume_parser.cli $LinkedInPdf -o $ResumeJson --personal-info $PersonalInfo --skills-csv $SkillsCsv --certifications-csv $CertificationsCsv --projects-csv $ProjectsCsv
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipEuropass) {
    if (-not (Test-Path $PersonalInfo)) {
        throw "personal_info.json not found: $PersonalInfo"
    }
    if (-not (Test-Path $EuropassConfig)) {
        throw "europass_config.json not found: $EuropassConfig"
    }

    python -m linkedin_resume_parser.europass $ResumeJson -m $PersonalInfo -c $EuropassConfig -o $EuropassXml
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Europass export failed (exit code $LASTEXITCODE). Continuing."
    }
}

$latexArgs = @()
$templatePath = $Template
$forcePdfLatexLocal = $ForcePdfLatex
if ($Basic) {
    $latexArgs += "--basic"
    if ($Template -eq "template.tex") {
        $templatePath = "template_basic.tex"
    }
    if ($TexOut -eq "${baseName}_SWE.tex") {
        $TexOut = "${baseName}_SWE_basic.tex"
    }
}

if ($Latinize) {
    $latexArgs += "--latinize"
    $forcePdfLatexLocal = $true
}

if ($Dark) {
    $latexArgs += "--dark"
}

python -m linkedin_resume_parser.latex $ResumeJson -t $templatePath -o $TexOut @latexArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$outputDir = Split-Path -Parent $TexOut
if (-not $outputDir) {
    $outputDir = "."
}

$pdfName = [IO.Path]::GetFileNameWithoutExtension($TexOut) + ".pdf"
$pdfPath = Join-Path $outputDir $pdfName

# If the PDF already exists, LaTeX (dvipdfmx) may fail to overwrite it when the file
# is open in a viewer (Windows file lock). Remove it up front for a clearer failure mode.
if (Test-Path $pdfPath) {
    try {
        Remove-Item -Force -ErrorAction Stop $pdfPath
    } catch {
        throw "Output PDF is locked or not writable: $pdfPath. Close any viewer holding it and re-run."
    }
}

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
