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
    [string]$EnvFile = "",
    [Parameter(Mandatory = $false)]
    [string]$PacketJson = "",
    [Parameter(Mandatory = $false)]
    [string]$PayloadJson = "",
    [Parameter(Mandatory = $false)]
    [string]$HandoffJson = "",
    [Parameter(Mandatory = $false)]
    [string]$AutofillJson = "",
    [Parameter(Mandatory = $false)]
    [string]$ArchitectureUploadPath = "docs/assets/qwencloud-architecture.png",
    [Parameter(Mandatory = $false)]
    [string]$LocalDemoVideoPath = "artifacts/qwencloud-proof/dream-qwencloud-devpost-final.mp4",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaProofVideoPath = "artifacts/qwencloud-proof/alibaba-deployment-proof.mp4",
    [switch]$SkipBackendDraft,
    [switch]$SkipExternalUrlChecks,
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")

$reportJson = Join-Path $OutputDir "devpost-materials-audit-$timestamp.json"
$reportMd = Join-Path $OutputDir "devpost-materials-audit-$timestamp.md"
$checks = @()
$publicTextItems = @()
$generatedArtifacts = @()
$sourceCodeUrl = if ($RepoRef -eq "main") { $RepoUrl } else { "$RepoUrl/tree/$RepoRef" }

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Add-PublicTextItem([string]$Source, [string]$Name, [object]$Value, [bool]$Required = $true) {
    $script:publicTextItems += [ordered]@{
        source = $Source
        name = $Name
        required = $Required
        value = Convert-ToText -Value $Value
    }
}

function Convert-ToText([object]$Value) {
    if ($null -eq $Value) { return "" }
    if ($Value -is [System.Array]) { return (($Value | ForEach-Object { Convert-ToText -Value $_ }) -join "`n") }
    return [string]$Value
}

function Get-Prop([object]$Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($property) { return $property.Value }
    return $null
}

function First-NonEmpty([object[]]$Values) {
    foreach ($value in $Values) {
        $text = Convert-ToText -Value $value
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            return $text
        }
    }
    return ""
}

function Is-HttpUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }
    if ($Url -match "[<>]|\.\.\.") { return $false }
    return [bool]($Url -match "^https?://")
}

function Normalize-Url([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return "" }
    return $Url.Trim().TrimEnd("/").ToLowerInvariant()
}

function Get-PowerShellExe {
    $pwsh = Get-Command "pwsh" -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $powershell = Get-Command "powershell" -ErrorAction SilentlyContinue
    if ($powershell) { return $powershell.Source }

    throw "PowerShell executable not found."
}

function Quote-ProcessArg([string]$Value) {
    if ($null -eq $Value) { return '""' }
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Get-ArgumentPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $Path }
    try {
        return Resolve-Path -LiteralPath $Path -Relative
    }
    catch {
        return $Path
    }
}

function Get-NewestFile([string]$Filter) {
    Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Invoke-MaterialProducer {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Filter,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    $stdout = Join-Path $OutputDir "devpost-materials-audit-$Name-$timestamp.out"
    $stderr = Join-Path $OutputDir "devpost-materials-audit-$Name-$timestamp.err"
    $startArguments = @($Arguments | ForEach-Object { Quote-ProcessArg $_ })
    $proc = Start-Process -FilePath (Get-PowerShellExe) -ArgumentList $startArguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $script:generatedArtifacts += [ordered]@{
        name = $Name
        exitCode = $proc.ExitCode
        stdout = $stdout
        stderr = $stderr
    }

    if ($proc.ExitCode -ne 0) {
        Add-Check -Name "generate.$Name" -Ok $false -Details "exit=$($proc.ExitCode); stdout=$stdout; stderr=$stderr"
        return ""
    }

    $after = @(Get-ChildItem -LiteralPath $OutputDir -Filter $Filter -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    $newest = @($after | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1)
    if (-not $newest) {
        $newest = @($after | Select-Object -First 1)
    }
    if (-not $newest) {
        Add-Check -Name "generate.$Name" -Ok $false -Details "no $Filter artifact found; stdout=$stdout; stderr=$stderr"
        return ""
    }

    Add-Check -Name "generate.$Name" -Ok $true -Details $newest.FullName -Required $false
    return $newest.FullName
}

function Resolve-JsonPath([string]$Path, [string]$Name, [string]$Filter, [string[]]$ProducerArgs) {
    if (-not [string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path)) {
        return (Resolve-Path -LiteralPath $Path).Path
    }

    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        Add-Check -Name "$Name.path_exists" -Ok $false -Details "missing: $Path"
        return ""
    }

    return Invoke-MaterialProducer -Name $Name -Filter $Filter -Arguments $ProducerArgs
}

function Read-JsonFile([string]$Path, [string]$Name) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        Add-Check -Name "$Name.json_readable" -Ok $false -Details "missing: $(if ($Path) { $Path } else { '<empty>' })"
        return $null
    }

    try {
        $data = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        Add-Check -Name "$Name.json_readable" -Ok $true -Details $Path
        return $data
    }
    catch {
        Add-Check -Name "$Name.json_readable" -Ok $false -Details $_.Exception.Message
        return $null
    }
}

function Test-FileAsset([string]$Name, [string]$Path, [int]$MinBytes = 1) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        Add-Check -Name $Name -Ok $false -Details "missing: $(if ($Path) { $Path } else { '<empty>' })"
        return
    }

    $item = Get-Item -LiteralPath $Path
    Add-Check -Name $Name -Ok ($item.Length -ge $MinBytes) -Details "path=$Path; size=$($item.Length)"
}

function Add-ObjectPropertiesAsPublicText([string]$Source, [object]$Object, [string[]]$OptionalNames = @()) {
    if ($null -eq $Object) { return }
    foreach ($property in $Object.PSObject.Properties) {
        if ($null -eq $property.Value) { continue }
        $required = $OptionalNames -notcontains $property.Name
        Add-PublicTextItem -Source $Source -Name $property.Name -Value $property.Value -Required $required
    }
}

function Get-PayloadField([object]$Payload, [string]$ElementId) {
    if ($null -eq $Payload) { return $null }
    return @($Payload.fields | Where-Object { $_.elementId -eq $ElementId } | Select-Object -First 1)
}

function Get-AssetPathFromObject([object]$Asset, [string]$Fallback) {
    $path = Convert-ToText -Value (Get-Prop -Object $Asset -Name "path")
    if (-not [string]::IsNullOrWhiteSpace($path)) { return $path }
    return $Fallback
}

$commonPacketArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-hackathon-submission-packet.ps1",
    "-RepoUrl", $RepoUrl,
    "-RepoRef", $RepoRef,
    "-OutputDir", $OutputDir,
    "-LocalVideoPath", $LocalDemoVideoPath,
    "-ArchitectureUploadPath", $ArchitectureUploadPath,
    "-AlibabaScreenshotPath", $AlibabaScreenshotPath,
    "-AlibabaProofVideoPath", $AlibabaProofVideoPath,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $commonPacketArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $commonPacketArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $commonPacketArgs += @("-BlogPostUrl", $BlogPostUrl) }
if ($SkipBackendDraft) { $commonPacketArgs += "-SkipBackendDraft" }
if ($SkipExternalUrlChecks) { $commonPacketArgs += "-SkipExternalUrlChecks" }

$commonPayloadArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-devpost-draft-payload.ps1",
    "-RepoUrl", $RepoUrl,
    "-RepoRef", $RepoRef,
    "-OutputDir", $OutputDir,
    "-ArchitectureUploadPath", $ArchitectureUploadPath,
    "-AlibabaScreenshotPath", $AlibabaScreenshotPath,
    "-AllowDraft"
)
if ($DemoVideoUrl) { $commonPayloadArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $commonPayloadArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $commonPayloadArgs += @("-BlogPostUrl", $BlogPostUrl) }

$commonHandoffArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-devpost-handoff.ps1",
    "-RepoUrl", $RepoUrl,
    "-RepoRef", $RepoRef,
    "-OutputDir", $OutputDir,
    "-ArchitectureUploadPath", $ArchitectureUploadPath,
    "-LocalDemoVideoPath", $LocalDemoVideoPath,
    "-AlibabaScreenshotPath", $AlibabaScreenshotPath,
    "-AlibabaProofVideoPath", $AlibabaProofVideoPath,
    "-AllowDraft"
)
if ($EnvFile) { $commonHandoffArgs += @("-EnvFile", $EnvFile) }
if ($DemoVideoUrl) { $commonHandoffArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $commonHandoffArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $commonHandoffArgs += @("-BlogPostUrl", $BlogPostUrl) }

$PacketJson = Resolve-JsonPath -Path $PacketJson -Name "packet" -Filter "devpost-submission-packet-*.json" -ProducerArgs $commonPacketArgs
$PayloadJson = Resolve-JsonPath -Path $PayloadJson -Name "payload" -Filter "devpost-draft-payload-*.json" -ProducerArgs $commonPayloadArgs
$HandoffJson = Resolve-JsonPath -Path $HandoffJson -Name "handoff" -Filter "devpost-handoff-*.json" -ProducerArgs $commonHandoffArgs

$autofillArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/qwencloud-devpost-autofill-snippet.ps1",
    "-RepoUrl", $RepoUrl,
    "-OutputDir", $OutputDir,
    "-PayloadJson", (Get-ArgumentPath -Path $PayloadJson),
    "-AllowDraft"
)
if ($DemoVideoUrl) { $autofillArgs += @("-DemoVideoUrl", $DemoVideoUrl) }
if ($BackendUrl) { $autofillArgs += @("-BackendUrl", $BackendUrl) }
if ($BlogPostUrl) { $autofillArgs += @("-BlogPostUrl", $BlogPostUrl) }
$AutofillJson = Resolve-JsonPath -Path $AutofillJson -Name "autofill" -Filter "devpost-autofill-snippet-*.json" -ProducerArgs $autofillArgs

$packet = Read-JsonFile -Path $PacketJson -Name "packet"
$payload = Read-JsonFile -Path $PayloadJson -Name "payload"
$handoff = Read-JsonFile -Path $HandoffJson -Name "handoff"
$autofill = Read-JsonFile -Path $AutofillJson -Name "autofill"

$packetProject = Get-Prop -Object $packet -Name "project"
$packetInfo = Get-Prop -Object $packet -Name "devpostAdditionalInfo"
$packetLinks = Get-Prop -Object $packet -Name "links"
$packetUploads = Get-Prop -Object $packet -Name "uploadAssets"
$payloadUploads = Get-Prop -Object $payload -Name "uploadAssets"
$payloadArchitecture = Get-Prop -Object $payloadUploads -Name "architectureDiagram"
$payloadAlibabaScreenshot = Get-Prop -Object $payloadUploads -Name "alibabaDeploymentScreenshot"
$handoffCopy = Get-Prop -Object $handoff -Name "copyFields"

Add-ObjectPropertiesAsPublicText -Source "packet.project" -Object $packetProject -OptionalNames @("blogPostUrl")
Add-ObjectPropertiesAsPublicText -Source "packet.devpostAdditionalInfo" -Object $packetInfo -OptionalNames @("blogSocialUrl", "blogPostUrl")
Add-ObjectPropertiesAsPublicText -Source "packet.links" -Object $packetLinks -OptionalNames @("buildJourneyDraft")
Add-ObjectPropertiesAsPublicText -Source "handoff.copyFields" -Object $handoffCopy -OptionalNames @("blogPostUrl")

foreach ($field in @($payload.fields)) {
    if ($null -eq $field) { continue }
    if ($field.inputKind -eq "file" -or $field.inputKind -eq "checkbox") { continue }
    Add-PublicTextItem -Source "payload.fields" -Name $field.elementId -Value $field.value -Required ([bool]$field.required)
}

$allPublicText = (($publicTextItems | ForEach-Object { $_.value }) -join "`n")
$requiredEmpty = @($publicTextItems | Where-Object { $_.required -and [string]::IsNullOrWhiteSpace($_.value) })
$placeholderRegex = "(?i)(<\s*(paste|public|deployed|backend|video|project|optional|url)[^>]*>|<[^>]*(api[-_ ]?key|access[-_ ]?key|secret)[^>]*>|TODO|TBD|\.\.\.)"
$secretRegex = "(?i)(dashscope[_-]?sk[_-][A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9_-]{20,}|DASHSCOPE_API_KEY\s*=\s*[""']?(?!<key>)(?!<judge-provided)[A-Za-z0-9_./+=-]{8,}|ALIBABA_CLOUD_ACCESS_KEY_SECRET\s*=\s*[""']?(?!<)[A-Za-z0-9_./+=-]{8,}|AccessKeySecret\s*[:=]\s*[""']?(?!<)[A-Za-z0-9_./+=-]{8,})"
$placeholderHits = @($publicTextItems | Where-Object { $_.required -and $_.value -match $placeholderRegex } | ForEach-Object { "$($_.source).$($_.name)" } | Sort-Object -Unique)
$secretHits = @($publicTextItems | Where-Object { $_.value -match $secretRegex } | ForEach-Object { "$($_.source).$($_.name)" } | Sort-Object -Unique)

$packetRepo = Convert-ToText -Value (Get-Prop -Object $packetProject -Name "repoUrl")
$payloadRepo = Convert-ToText -Value (Get-Prop -Object $payload -Name "repoUrl")
$handoffRepo = Convert-ToText -Value (Get-Prop -Object $handoff -Name "repoUrl")
$repoValues = @($RepoUrl, $packetRepo, $payloadRepo, $handoffRepo) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

$packetDemo = Convert-ToText -Value (Get-Prop -Object $packetProject -Name "demoVideoUrl")
$payloadDemo = Convert-ToText -Value (Get-Prop -Object $payload -Name "demoVideoUrl")
$handoffDemo = Convert-ToText -Value (Get-Prop -Object $handoff -Name "demoVideoUrl")
$demoUsed = First-NonEmpty -Values @($DemoVideoUrl, $packetDemo, $payloadDemo, $handoffDemo)
$demoValues = @($packetDemo, $payloadDemo, $handoffDemo) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

$packetBackend = Convert-ToText -Value (Get-Prop -Object $packetProject -Name "backendUrl")
$payloadBackend = Convert-ToText -Value (Get-Prop -Object $payload -Name "backendUrl")
$handoffBackend = Convert-ToText -Value (Get-Prop -Object $handoff -Name "backendUrl")
$backendUsed = First-NonEmpty -Values @($BackendUrl, $packetBackend, $payloadBackend, $handoffBackend)
$backendValues = @($packetBackend, $payloadBackend, $handoffBackend) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

$architecturePath = Get-AssetPathFromObject -Asset $payloadArchitecture -Fallback (First-NonEmpty -Values @((Get-Prop -Object $packetUploads -Name "architectureDiagram"), $ArchitectureUploadPath))
$alibabaScreenshotAuditPath = Get-AssetPathFromObject -Asset $payloadAlibabaScreenshot -Fallback (First-NonEmpty -Values @((Get-Prop -Object $packetUploads -Name "alibabaDeploymentScreenshot"), $AlibabaScreenshotPath))
$alibabaProofAuditPath = First-NonEmpty -Values @((Get-Prop -Object $packetUploads -Name "alibabaDeploymentProofVideo"), $AlibabaProofVideoPath)

Add-Check -Name "packet_ready_for_devpost" -Ok ([bool](Get-Prop -Object $packet -Name "readyForDevpost")) -Details "readyForDevpost=$([bool](Get-Prop -Object $packet -Name 'readyForDevpost'))"
Add-Check -Name "payload_ready_for_final_fields" -Ok ([bool](Get-Prop -Object $payload -Name "readyForFinalDevpostFields")) -Details "readyForFinalDevpostFields=$([bool](Get-Prop -Object $payload -Name 'readyForFinalDevpostFields'))"
Add-Check -Name "payload_ready_for_public_text_autofill" -Ok ([bool](Get-Prop -Object $payload -Name "readyForPublicTextAutofill")) -Details "readyForPublicTextAutofill=$([bool](Get-Prop -Object $payload -Name 'readyForPublicTextAutofill'))"
Add-Check -Name "handoff_ready_for_final_submit" -Ok ([bool](Get-Prop -Object $handoff -Name "readyForDevpostFinalSubmit")) -Details "readyForDevpostFinalSubmit=$([bool](Get-Prop -Object $handoff -Name 'readyForDevpostFinalSubmit'))"
Add-Check -Name "autofill_snippet_ready" -Ok ([bool](Get-Prop -Object $autofill -Name "readyForAutofillSnippet")) -Details "readyForAutofillSnippet=$([bool](Get-Prop -Object $autofill -Name 'readyForAutofillSnippet'))"

Add-Check -Name "project_title_mentions_dream_qwen_memoryagent" -Ok (($allPublicText -match "\bDREAM\b") -and ($allPublicText -match "Qwen Cloud") -and ($allPublicText -match "MemoryAgent")) -Details "public copy identity"
Add-Check -Name "track_1_memoryagent_present" -Ok ($allPublicText -match "Track 1:\s*MemoryAgent") -Details "Track 1: MemoryAgent"
Add-Check -Name "public_copy_mentions_alibaba_cloud" -Ok ($allPublicText -match "Alibaba Cloud") -Details "Alibaba Cloud deployment framing"
Add-Check -Name "required_public_copy_fields_present" -Ok ($requiredEmpty.Count -eq 0) -Details $(if ($requiredEmpty.Count -eq 0) { "all required public fields have values" } else { "empty=$(@($requiredEmpty | ForEach-Object { "$($_.source).$($_.name)" }) -join ', ')" })
Add-Check -Name "placeholder_free_public_copy" -Ok ($placeholderHits.Count -eq 0) -Details $(if ($placeholderHits.Count -eq 0) { "no placeholder tokens in public copy" } else { "hits=$($placeholderHits -join ', ')" })
Add-Check -Name "secret_free_public_copy" -Ok ($secretHits.Count -eq 0) -Details $(if ($secretHits.Count -eq 0) { "no secret-looking values in public copy" } else { "hits=$($secretHits -join ', ')" })

Add-Check -Name "repo_url_present" -Ok (Is-HttpUrl $RepoUrl) -Details $RepoUrl
$repoConsistent = (@($repoValues | ForEach-Object { Normalize-Url $_ } | Sort-Object -Unique).Count -le 1)
Add-Check -Name "repo_url_consistent_across_materials" -Ok $repoConsistent -Details "values=$(@($repoValues | Sort-Object -Unique) -join ', ')"
$sourceField = Get-PayloadField -Payload $payload -ElementId "participants_submission_requirements_submission_field_values_attributes_7_value"
$sourceFieldValue = Convert-ToText -Value (Get-Prop -Object $sourceField -Name "value")
$competitionSourceValues = @(
    (Get-Prop -Object $packetProject -Name "sourceCodeUrl")
    (Get-Prop -Object $packetInfo -Name "repositoryUrl")
    (Get-Prop -Object $payload -Name "sourceCodeUrl")
    $sourceFieldValue
    (Get-Prop -Object $handoff -Name "sourceCodeUrl")
    (Get-Prop -Object $handoffCopy -Name "repoUrl")
) | ForEach-Object { Convert-ToText -Value $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$competitionSourceUrls = @($competitionSourceValues | ForEach-Object { Normalize-Url $_ } | Sort-Object -Unique)
$sourceRefApplied = ($competitionSourceUrls.Count -eq 1) -and ($competitionSourceUrls[0] -eq (Normalize-Url $sourceCodeUrl))
Add-Check -Name "competition_source_ref_applied" -Ok $sourceRefApplied -Details "expected=$sourceCodeUrl; values=$($competitionSourceValues -join ', ')"
Add-Check -Name "demo_video_url_present" -Ok (-not [string]::IsNullOrWhiteSpace($demoUsed)) -Details $(if ($demoUsed) { $demoUsed } else { "missing" })
Add-Check -Name "demo_video_url_devpost_rules_platform" -Ok (Test-QwenCloudDevpostVideoUrl -Url $demoUsed) -Details $(if ($demoUsed) { $demoUsed } else { "missing" })
$demoConsistent = if ($demoValues.Count -gt 0) { (@($demoValues | ForEach-Object { Normalize-Url $_ } | Sort-Object -Unique).Count -eq 1) } else { $false }
Add-Check -Name "demo_video_url_consistent_across_materials" -Ok $demoConsistent -Details "values=$(@($demoValues | Sort-Object -Unique) -join ', ')"
Add-Check -Name "backend_url_present" -Ok (Is-HttpUrl $backendUsed) -Details $(if ($backendUsed) { $backendUsed } else { "missing" })
$backendConsistent = if ($backendValues.Count -gt 0) { (@($backendValues | ForEach-Object { Normalize-Url $_ } | Sort-Object -Unique).Count -eq 1) } else { $false }
Add-Check -Name "backend_url_consistent_across_materials" -Ok $backendConsistent -Details "values=$(@($backendValues | Sort-Object -Unique) -join ', ')"

foreach ($elementId in @(
    "software_description",
    "software_tag_list",
    "software_urls_attributes_0_url",
    "software_video_url",
    "participants_submission_requirements_submission_field_values_attributes_6_value",
    "participants_submission_requirements_submission_field_values_attributes_7_value",
    "participants_submission_requirements_submission_field_values_attributes_8_value"
)) {
    $field = Get-PayloadField -Payload $payload -ElementId $elementId
    Add-Check -Name "payload_field.$elementId" -Ok ($null -ne $field -and -not [string]::IsNullOrWhiteSpace([string]$field.value)) -Details $(if ($field) { $field.label } else { "missing field" })
}

$legalFields = @($payload.fields | Where-Object { $_.inputKind -eq "checkbox" -or $_.label -match "attestation" })
$legalOk = ($legalFields.Count -ge 3) -and (@($legalFields | Where-Object { $_.safeForNonLegalDraftSave -or -not [string]::IsNullOrWhiteSpace([string]$_.value) }).Count -eq 0)
Add-Check -Name "legal_attestations_excluded_from_public_payload" -Ok $legalOk -Details "legalFieldCount=$($legalFields.Count)"
$actionConfirmations = @($handoff.actionTimeConfirmations)
Add-Check -Name "external_write_confirmation_required" -Ok ([bool](Get-Prop -Object $payload -Name "externalWriteRequiresActionTimeConfirmation") -and [bool](Get-Prop -Object $autofill -Name "externalWriteRequiresActionTimeConfirmation") -and $actionConfirmations.Count -ge 4) -Details "handoffConfirmations=$($actionConfirmations.Count)"
$autofillWarnings = (@($autofill.warnings) -join " ")
Add-Check -Name "autofill_does_not_save_upload_or_submit" -Ok (($autofillWarnings -match "does not") -and ($autofillWarnings -match "Save|save") -and ($autofillWarnings -match "upload") -and ($autofillWarnings -match "submit")) -Details "autofill warnings"

Add-Check -Name "testing_and_rights_notes_link_present" -Ok (Is-HttpUrl (Convert-ToText -Value (Get-Prop -Object $packetLinks -Name "testingAndRightsNotes"))) -Details (Convert-ToText -Value (Get-Prop -Object $packetLinks -Name "testingAndRightsNotes"))
Test-FileAsset -Name "architecture_upload_asset_exists" -Path $architecturePath
Test-FileAsset -Name "alibaba_deployment_screenshot_exists" -Path $alibabaScreenshotAuditPath
Test-FileAsset -Name "alibaba_backend_proof_recording_exists" -Path $alibabaProofAuditPath

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok } | ForEach-Object { $_.name })
$ready = $requiredFailures.Count -eq 0
$status = if ($ready) { "READY" } else { "DRAFT" }

$result = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForDevpostMaterials = $ready
    repoUrl = $RepoUrl
    repoRef = $RepoRef
    sourceCodeUrl = $sourceCodeUrl
    demoVideoUrl = $demoUsed
    backendUrl = $backendUsed
    blogPostUrl = $BlogPostUrl
    packetJson = $PacketJson
    payloadJson = $PayloadJson
    handoffJson = $HandoffJson
    autofillJson = $AutofillJson
    reportJson = $reportJson
    reportMarkdown = $reportMd
    generatedArtifacts = $generatedArtifacts
    publicTextItemCount = $publicTextItems.Count
    placeholderHits = $placeholderHits
    secretHits = $secretHits
    checks = $checks
    requiredFailures = $requiredFailures
    warnings = @(
        "This audit reads local generated materials only. It does not save Devpost fields, upload files, check legal boxes, or final-submit.",
        "Command examples may mention environment variable names; the secret gate blocks secret-looking values and public-copy placeholders."
    )
}
Set-Content -Path $reportJson -Value ($result | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Devpost Materials Audit ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for Devpost materials: $ready",
    "- Repo: $sourceCodeUrl",
    "- Demo video URL: $(if ($demoUsed) { $demoUsed } else { '<missing>' })",
    "- Backend URL: $(if ($backendUsed) { $backendUsed } else { '<missing>' })",
    "- Packet JSON: $(if ($PacketJson) { $PacketJson } else { '<missing>' })",
    "- Draft payload JSON: $(if ($PayloadJson) { $PayloadJson } else { '<missing>' })",
    "- Handoff JSON: $(if ($HandoffJson) { $HandoffJson } else { '<missing>' })",
    "- Autofill JSON: $(if ($AutofillJson) { $AutofillJson } else { '<missing>' })",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)

foreach ($check in $checks) {
    $required = if ($check.required) { "yes" } else { "no" }
    $resultText = if ($check.ok) { "PASS" } else { "FAIL" }
    $lines += "| $($check.name) | $required | $resultText | $($check.details -replace '\|', '/') |"
}

if ($requiredFailures.Count -gt 0) {
    $lines += @(
        "",
        "## Missing Required Items",
        ""
    )
    foreach ($failure in $requiredFailures) {
        $lines += "- $failure"
    }
}

$lines += @(
    "",
    "## Safe Boundary",
    "",
    "This audit does not write to Devpost. Save public fields, upload files, legal attestations, and final Submit still require Zack action-time confirmation."
)
Set-Content -Path $reportMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($ready) {
    Write-Host "Devpost materials audit READY: $reportMd"
}
else {
    Write-Host "Devpost materials audit DRAFT: $reportMd" -ForegroundColor Yellow
    Write-Host "Missing required checks: $($requiredFailures -join ', ')"
}
Write-Host "JSON: $reportJson"

if (-not $ready -and -not $AllowDraft) {
    exit 1
}
