param(
    [Parameter(Mandatory = $true)]
    [string]$LinkedInPdf,
    [string]$ResumeJson,
    [string]$PersonalInfo = "personal_info.json",
    [string]$Template = "template.tex",
    [string]$TexOut,
    [string]$EuropassXml,
    [string]$EuropassConfig = "europass_config.json",
    [switch]$SkipEuropass
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

if (-not (Get-Command pdflatex -ErrorAction SilentlyContinue)) {
    throw "pdflatex not found. Install MiKTeX or TeX Live and ensure it is on PATH."
}

python -m linkedin_resume_parser.cli $LinkedInPdf -o $ResumeJson
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (Test-Path $PersonalInfo) {
    $resume = Get-Content $ResumeJson -Raw | ConvertFrom-Json
    $personal = Get-Content $PersonalInfo -Raw | ConvertFrom-Json

    if ($personal.skills) {
        if (-not $resume.skills) {
            $resume.skills = @()
        }

        $existing = @{}
        foreach ($entry in $resume.skills) {
            if ($null -ne $entry.name) {
                $existing[$entry.name.ToString().Trim().ToLowerInvariant()] = $true
            }
        }

        foreach ($name in $personal.skills) {
            $cleanName = $name.ToString().Trim()
            if ($cleanName.Length -gt 0 -and -not $existing.ContainsKey($cleanName.ToLowerInvariant())) {
                $resume.skills += [pscustomobject]@{ name = $cleanName }
                $existing[$cleanName.ToLowerInvariant()] = $true
            }
        }

        $resume | ConvertTo-Json -Depth 10 | Set-Content -Path $ResumeJson -Encoding UTF8
    }
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
        exit $LASTEXITCODE
    }
}

python -m linkedin_resume_parser.latex $ResumeJson -t $Template -o $TexOut
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$outputDir = Split-Path -Parent $TexOut
if (-not $outputDir) {
    $outputDir = "."
}

pdflatex -interaction=nonstopmode -halt-on-error -output-directory $outputDir $TexOut 2>&1 | Out-Null
exit $LASTEXITCODE
