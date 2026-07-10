param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/zemeng2015/dream-ai-engineering-copilot",
    [Parameter(Mandatory = $false)]
    [string]$RepoRef = "codex/champion-memory-loop",
    [Parameter(Mandatory = $false)]
    [string]$DemoVideoUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$BlogPostUrl = "",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "artifacts/qwencloud-proof",
    [Parameter(Mandatory = $false)]
    [string]$PayloadJson = "",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$reportJson = Join-Path $OutputDir "devpost-autofill-snippet-$timestamp.json"
$reportMd = Join-Path $OutputDir "devpost-autofill-snippet-$timestamp.md"
$snippetJs = Join-Path $OutputDir "devpost-autofill-snippet-$timestamp.js"

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Get-LatestPayloadJson {
    Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-draft-payload-*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

if ([string]::IsNullOrWhiteSpace($PayloadJson)) {
    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-draft-payload-*.json" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/qwencloud-devpost-draft-payload.ps1",
        "-RepoUrl", $RepoUrl,
        "-RepoRef", $RepoRef,
        "-OutputDir", $OutputDir,
        "-AllowDraft"
    )
    if ($DemoVideoUrl) { $args += @("-DemoVideoUrl", $DemoVideoUrl) }
    if ($BackendUrl) { $args += @("-BackendUrl", $BackendUrl) }
    if ($BlogPostUrl) { $args += @("-BlogPostUrl", $BlogPostUrl) }

    $stdout = Join-Path $OutputDir "devpost-autofill-snippet-payload-$timestamp.out"
    $stderr = Join-Path $OutputDir "devpost-autofill-snippet-payload-$timestamp.err"
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -ne 0) {
        throw "Devpost draft payload generation failed. See $stderr"
    }

    $latest = Get-LatestPayloadJson
    $newest = @(Get-ChildItem -LiteralPath $OutputDir -Filter "devpost-draft-payload-*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Where-Object { $before -notcontains $_.FullName } |
        Select-Object -First 1)
    if ($newest) {
        $PayloadJson = $newest.FullName
    }
    elseif ($latest) {
        $PayloadJson = $latest.FullName
    }
}

if ([string]::IsNullOrWhiteSpace($PayloadJson) -or -not (Test-Path $PayloadJson)) {
    throw "PayloadJson not found. Generate it with scripts/qwencloud-devpost-draft-payload.ps1 first."
}

$payload = Get-Content -LiteralPath $PayloadJson -Raw | ConvertFrom-Json
$safeFields = @(
    $payload.fields |
        Where-Object {
            $_.safeForNonLegalDraftSave -and
            $_.present -and
            $_.inputKind -ne "file" -and
            $_.inputKind -ne "checkbox"
        } |
        Select-Object page, elementId, label, value, inputKind, notes
)
$excludedFields = @(
    $payload.fields |
        Where-Object {
            -not $_.safeForNonLegalDraftSave -or
            -not $_.present -or
            $_.inputKind -eq "file" -or
            $_.inputKind -eq "checkbox"
        } |
        Select-Object page, elementId, label, inputKind, present, safeForNonLegalDraftSave, notes
)

$safeFieldsJson = if ($safeFields.Count -gt 0) {
    $safeFields | ConvertTo-Json -Depth 10 -Compress
}
else {
    "[]"
}

$snippetTemplate = @'
(function () {
  "use strict";

  const fields = __FIELDS_JSON__;
  const results = [];

  function byIdOrName(id) {
    const byId = document.getElementById(id);
    if (byId) return byId;
    try {
      return document.querySelector('[name="' + String(id).replace(/"/g, '\\"') + '"]');
    } catch (err) {
      return null;
    }
  }

  function dispatch(el) {
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function setValue(el, value) {
    const tag = (el.tagName || "").toLowerCase();
    if (tag === "select") {
      const wanted = String(value).trim().toLowerCase();
      const option = Array.from(el.options || []).find((candidate) => {
        const text = String(candidate.text || "").trim().toLowerCase();
        const optionValue = String(candidate.value || "").trim().toLowerCase();
        return text === wanted || optionValue === wanted || text.includes(wanted);
      });
      if (!option) return false;
      el.value = option.value;
      dispatch(el);
      return true;
    }

    const proto = Object.getPrototypeOf(el);
    const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
    if (descriptor && descriptor.set) {
      descriptor.set.call(el, value);
    } else {
      el.value = value;
    }
    dispatch(el);
    return true;
  }

  function detectPage() {
    const path = String(window.location.pathname || "").toLowerCase();
    if (path.includes("additional-info")) return "additional_info";
    if (path.includes("project_details")) return "project_details";
    return "";
  }

  function fillDevpostDraft(page) {
    const activePage = page || detectPage();
    const pageFields = activePage ? fields.filter((field) => field.page === activePage) : fields;
    for (const field of pageFields) {
      const el = byIdOrName(field.elementId);
      if (!el) {
        results.push({ status: "missing", page: field.page, elementId: field.elementId, label: field.label, value: field.value });
        continue;
      }
      const ok = setValue(el, field.value);
      results.push({ status: ok ? "filled" : "copy_manually", page: field.page, elementId: field.elementId, label: field.label, value: field.value });
    }
    console.table(results);
    console.info("DREAM Devpost autofill finished. Review the fields manually. This snippet does not upload files, check legal boxes, click Save, or submit.");
    return results;
  }

  window.DREAM_DEVPOST_AUTOFILL = { fields, fillDevpostDraft };
  fillDevpostDraft();
})();
'@

$snippet = $snippetTemplate.Replace("__FIELDS_JSON__", $safeFieldsJson)
Set-Content -Path $snippetJs -Value $snippet -Encoding UTF8

$readyForSnippet = $safeFields.Count -gt 0
$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    readyForAutofillSnippet = $readyForSnippet
    payloadJson = (Resolve-Path $PayloadJson).Path
    snippetJavaScript = $snippetJs
    markdown = $reportMd
    safeFieldCount = $safeFields.Count
    excludedFieldCount = $excludedFields.Count
    externalWriteRequiresActionTimeConfirmation = $true
    warnings = @(
        "This snippet only fills visible non-legal public text/link fields.",
        "It does not click Save, upload files, check legal attestations, or final-submit.",
        "Review every filled field in Devpost before saving."
    )
    safeFields = $safeFields
    excludedFields = $excludedFields
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Devpost Autofill Snippet ($timestamp)",
    "",
    "- Ready for autofill snippet: $readyForSnippet",
    "- Payload JSON: $((Resolve-Path $PayloadJson).Path)",
    "- Snippet JS: $snippetJs",
    "- Safe fields: $($safeFields.Count)",
    "- Excluded fields: $($excludedFields.Count)",
    "- External write requires action-time confirmation: yes",
    "",
    "## How To Use",
    "",
    "1. Open the matching Devpost draft page.",
    "2. Open the browser developer console.",
    "3. Paste the generated JavaScript from ``$snippetJs``.",
    "4. Review every filled field manually.",
    "5. Save only after Zack confirms the external write at action time.",
    "",
    "The snippet does not upload files, check legal boxes, click Save, or submit.",
    "",
    "## Safe Fields",
    "",
    "| Page | Element ID | Kind | Label | Value |",
    "|---|---|---|---|---|"
)
foreach ($field in $safeFields) {
    $value = ([string]$field.value -replace "`r?`n", "<br>") -replace "\|", "/"
    $lines += "| $($field.page) | $($field.elementId) | $($field.inputKind) | $($field.label -replace '\|', '/') | $value |"
}

$lines += @(
    "",
    "## Excluded Fields",
    "",
    "| Page | Element ID | Kind | Present | Safe | Label / Notes |",
    "|---|---|---|---:|---:|---|"
)
foreach ($field in $excludedFields) {
    $notes = if ([string]::IsNullOrWhiteSpace($field.notes)) { $field.label } else { "$($field.label): $($field.notes)" }
    $lines += "| $($field.page) | $($field.elementId) | $($field.inputKind) | $(if ($field.present) { 'yes' } else { 'no' }) | $(if ($field.safeForNonLegalDraftSave) { 'yes' } else { 'no' }) | $($notes -replace '\|', '/') |"
}

Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($readyForSnippet) {
    Write-Host "Devpost autofill snippet READY: $reportMd"
    Write-Host "JS: $snippetJs"
}
else {
    Write-Host "Devpost autofill snippet DRAFT: $reportMd" -ForegroundColor Yellow
    if (-not $AllowDraft) {
        exit 1
    }
}
