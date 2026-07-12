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
    [string]$ProjectStoryPath = "docs/qwencloud-devpost-story.md",
    [Parameter(Mandatory = $false)]
    [string]$ArchitectureUploadPath = "docs/assets/qwencloud-architecture.png",
    [Parameter(Mandatory = $false)]
    [string]$AlibabaScreenshotPath = "artifacts/qwencloud-proof/alibaba-deployment-screenshot.png",
    [switch]$AllowDraft
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
. (Join-Path $PSScriptRoot "qwencloud-devpost-video-url.ps1")
. (Join-Path $PSScriptRoot "qwencloud-devpost-copy.ps1")

$payloadJson = Join-Path $OutputDir "devpost-draft-payload-$timestamp.json"
$payloadMd = Join-Path $OutputDir "devpost-draft-payload-$timestamp.md"
$fields = @()
$checks = @()

$devpostCopy = Get-QwenCloudDevpostCopy -StoryPath $ProjectStoryPath
$projectTitle = $devpostCopy.projectTitle
$track = $devpostCopy.track
$projectDetailsUrl = "https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/project_details/edit"
$additionalInfoUrl = "https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/additional-info/edit"
$finalizationUrl = "https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1073064-dream-qwen-cloud-memoryagent/finalization"
$sourceCodeUrl = if ($RepoRef -eq "main") { $RepoUrl } else { "$RepoUrl/tree/$RepoRef" }
$deploymentProofUrl = "$RepoUrl/blob/$RepoRef/deploy/alibaba/serverless-devs-runtime.yaml"
$tryItOutUrl = if (-not [string]::IsNullOrWhiteSpace($BackendUrl)) { $BackendUrl } else { "" }
$builtWith = $devpostCopy.builtWith
$aiTools = "Qwen Cloud for the runtime LLM provider, OpenAI Codex for implementation assistance, GitHub Actions for CI verification, and local automation scripts for audit, render, deploy preflight, and submission packet generation."
$preExistingExplanation = $devpostCopy.preExistingExplanation
$projectStory = $devpostCopy.story

function Add-Check([string]$Name, [bool]$Ok, [string]$Details, [bool]$Required = $true) {
    $script:checks += [ordered]@{
        name = $Name
        ok = $Ok
        required = $Required
        details = $Details
    }
}

function Add-Field {
    param(
        [string]$Page,
        [string]$ElementId,
        [string]$Label,
        [string]$Value,
        [string]$InputKind,
        [bool]$Required = $true,
        [bool]$SafeForNonLegalDraftSave = $true,
        [bool]$RequiresActionTimeConfirmation = $true,
        [string]$Notes = ""
    )

    $script:fields += [ordered]@{
        page = $Page
        elementId = $ElementId
        label = $Label
        value = $Value
        inputKind = $InputKind
        required = $Required
        present = -not [string]::IsNullOrWhiteSpace($Value)
        safeForNonLegalDraftSave = $SafeForNonLegalDraftSave
        requiresActionTimeConfirmation = $RequiresActionTimeConfirmation
        notes = $Notes
    }
}

function Is-HttpUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }
    if ($Url -match "[<>]|\.\.\.") { return $false }
    return [bool]($Url -match "^https?://")
}

function Is-DevpostRulesVideoUrl([string]$Url) {
    return Test-QwenCloudDevpostVideoUrl -Url $Url
}

function Get-AssetState([string]$Path) {
    if (-not (Test-Path $Path)) {
        return [ordered]@{
            path = $Path
            exists = $false
            absolutePath = [System.IO.Path]::GetFullPath($Path)
            size = 0
        }
    }

    $item = Get-Item -LiteralPath $Path
    return [ordered]@{
        path = $Path
        exists = $true
        absolutePath = $item.FullName
        size = $item.Length
    }
}

Add-Field -Page "project_details" -ElementId "software_description" -Label "About the project" -Value $projectStory.Trim() -InputKind "textarea"
Add-Field -Page "project_details" -ElementId "software_tag_list" -Label "Built with" -Value $builtWith -InputKind "tag_list"
Add-Field -Page "project_details" -ElementId "software_urls_attributes_0_url" -Label "Try it out" -Value $tryItOutUrl -InputKind "url" -Notes "Use the deployed Alibaba Function Compute backend URL. The source repo is supplied in the required repository field."
Add-Field -Page "project_details" -ElementId "software_video_url" -Label "Video demo link" -Value $DemoVideoUrl -InputKind "url" -SafeForNonLegalDraftSave (Is-DevpostRulesVideoUrl $DemoVideoUrl) -Notes "Required by Devpost; must be public YouTube, Vimeo, Facebook Video, or Youku."

Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_0_value" -Label "Submitter type" -Value "Individual" -InputKind "select"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_2_values" -Label "Country of residence" -Value "United States" -InputKind "multi_select"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_3_value" -Label "Newly built or previously existing project" -Value "New" -InputKind "select"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_4_value" -Label "Project start date" -Value "06-21-26" -InputKind "text"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_5_value" -Label "Pre-existing project explanation" -Value $preExistingExplanation -InputKind "textarea"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_6_value" -Label "Selected Track" -Value $track -InputKind "select"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_7_value" -Label "Code repository URL" -Value $sourceCodeUrl -InputKind "text"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_8_value" -Label "Alibaba deployment proof code URL" -Value $deploymentProofUrl -InputKind "text"
Add-Field -Page "additional_info" -ElementId "submission_field_file_27544_add_files" -Label "Architecture diagram upload" -Value $ArchitectureUploadPath -InputKind "file" -SafeForNonLegalDraftSave $false -Notes "File upload requires action-time confirmation."
Add-Field -Page "additional_info" -ElementId "submission_field_file_27832_add_files" -Label "Alibaba deployment screenshot upload" -Value $AlibabaScreenshotPath -InputKind "file" -SafeForNonLegalDraftSave $false -Notes "File upload requires action-time confirmation and real Alibaba backend proof."
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_11_value" -Label "Blog/social journey URL" -Value $BlogPostUrl -InputKind "text" -Required $false
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_12_value" -Label "AI tools leveraged" -Value $aiTools -InputKind "textarea"
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_13_value" -Label "Learning level" -Value "Significant" -InputKind "select"

Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_14_value" -Label "Age of majority attestation" -Value "" -InputKind "checkbox" -SafeForNonLegalDraftSave $false -Notes "Excluded from payload. Zack must personally confirm."
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_15_value" -Label "Eligible jurisdiction attestation" -Value "" -InputKind "checkbox" -SafeForNonLegalDraftSave $false -Notes "Excluded from payload. Zack must personally confirm."
Add-Field -Page "additional_info" -ElementId "participants_submission_requirements_submission_field_values_attributes_16_value" -Label "Not sponsor/government employee attestation" -Value "" -InputKind "checkbox" -SafeForNonLegalDraftSave $false -Notes "Excluded from payload. Zack must personally confirm."

$architectureAsset = Get-AssetState -Path $ArchitectureUploadPath
$alibabaScreenshotAsset = Get-AssetState -Path $AlibabaScreenshotPath

Add-Check -Name "project_story_present" -Ok (-not [string]::IsNullOrWhiteSpace($projectStory)) -Details "software_description"
Add-Check -Name "project_story_v3_cloud_proof" -Ok (($projectStory -match "Alibaba Tablestore") -and ($projectStory -match "cross-instance") -and ($projectStory -match "20/20") -and ($projectStory -notmatch "(?i)SQLite")) -Details "sha256=$($devpostCopy.storySha256)"
Add-Check -Name "built_with_present" -Ok (-not [string]::IsNullOrWhiteSpace($builtWith)) -Details "software_tag_list"
Add-Check -Name "repo_url_present" -Ok (Is-HttpUrl $RepoUrl) -Details $RepoUrl
Add-Check -Name "working_project_url_present" -Ok (Is-HttpUrl $tryItOutUrl) -Details $(if ($tryItOutUrl) { $tryItOutUrl } else { "missing deployed Alibaba backend URL" })
Add-Check -Name "demo_video_url_present" -Ok (-not [string]::IsNullOrWhiteSpace($DemoVideoUrl)) -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
Add-Check -Name "demo_video_url_devpost_rules_platform" -Ok (Is-DevpostRulesVideoUrl $DemoVideoUrl) -Details $(if ($DemoVideoUrl) { $DemoVideoUrl } else { "missing" })
Add-Check -Name "deployment_proof_code_url_present" -Ok (Is-HttpUrl $deploymentProofUrl) -Details $deploymentProofUrl
Add-Check -Name "architecture_upload_asset_exists" -Ok ([bool]$architectureAsset.exists) -Details "$($architectureAsset.path); size=$($architectureAsset.size)"
Add-Check -Name "alibaba_screenshot_asset_exists" -Ok ([bool]$alibabaScreenshotAsset.exists) -Details "$($alibabaScreenshotAsset.path); size=$($alibabaScreenshotAsset.size)"
Add-Check -Name "legal_attestations_excluded" -Ok $true -Details "legal checkboxes are not included in non-legal draft payload"
Add-Check -Name "external_write_confirmation_required" -Ok $true -Details "saving Devpost draft fields is an external write action"

$requiredFailures = @($checks | Where-Object { $_.required -and -not $_.ok })
$nonLegalTextFailures = @(
    $fields |
        Where-Object {
            $_.required -and
            $_.safeForNonLegalDraftSave -and
            $_.inputKind -ne "file" -and
            -not $_.present
        } |
        ForEach-Object { $_.elementId }
)
$readyForPublicTextAutofill = $nonLegalTextFailures.Count -eq 0
$readyForFinalDevpostFields = $requiredFailures.Count -eq 0
$status = if ($readyForFinalDevpostFields) { "READY" } else { "DRAFT" }

$payload = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    readyForPublicTextAutofill = $readyForPublicTextAutofill
    readyForFinalDevpostFields = $readyForFinalDevpostFields
    externalWriteRequiresActionTimeConfirmation = $true
    repoUrl = $RepoUrl
    repoRef = $RepoRef
    sourceCodeUrl = $sourceCodeUrl
    demoVideoUrl = $DemoVideoUrl
    backendUrl = $BackendUrl
    blogPostUrl = $BlogPostUrl
    publicCopy = [ordered]@{
        story = $projectStory
        storyPath = $devpostCopy.storyPath
        storySha256 = $devpostCopy.storySha256
        builtWith = $builtWith
    }
    liveDevpostDraft = [ordered]@{
        projectDetailsUrl = $projectDetailsUrl
        additionalInfoUrl = $additionalInfoUrl
        finalizationUrl = $finalizationUrl
    }
    uploadAssets = [ordered]@{
        architectureDiagram = $architectureAsset
        alibabaDeploymentScreenshot = $alibabaScreenshotAsset
    }
    fields = $fields
    checks = $checks
    requiredFailures = @($requiredFailures | ForEach-Object { $_.name })
    nonLegalTextFailures = $nonLegalTextFailures
    warnings = @(
        "Do not save these fields to Devpost without Zack action-time confirmation.",
        "Do not upload files, check legal attestations, or click final Submit from this payload.",
        "The demo video URL must be a public YouTube, Vimeo, Facebook Video, or Youku URL."
    )
}
Set-Content -Path $payloadJson -Value ($payload | ConvertTo-Json -Depth 12) -Encoding UTF8

$lines = @(
    "# Qwen Cloud Devpost Draft Payload ($timestamp)",
    "",
    "- Status: $status",
    "- Ready for public text autofill: $readyForPublicTextAutofill",
    "- Ready for final Devpost fields: $readyForFinalDevpostFields",
    "- External write requires action-time confirmation: yes",
    "- Project details: $projectDetailsUrl",
    "- Additional info: $additionalInfoUrl",
    "- Finalization: $finalizationUrl",
    "",
    "## Checks",
    "",
    "| Check | Required | Result | Details |",
    "|---|---:|---:|---|"
)
foreach ($check in $checks) {
    $lines += "| $($check.name) | $(if ($check.required) { 'yes' } else { 'no' }) | $(if ($check.ok) { 'PASS' } else { 'FAIL' }) | $($check.details -replace '\|', '/') |"
}

if ($requiredFailures.Count -gt 0) {
    $lines += @(
        "",
        "## Missing Required Items",
        ""
    )
    foreach ($failure in $requiredFailures) {
        $lines += "- $($failure.name): $($failure.details)"
    }
}

$lines += @(
    "",
    "## Fields",
    "",
    "| Page | Element ID | Kind | Required | Safe for non-legal draft save | Present | Label | Value / Notes |",
    "|---|---|---|---:|---:|---:|---|---|"
)
foreach ($field in $fields) {
    $value = if ([string]::IsNullOrWhiteSpace($field.value)) { $field.notes } else { $field.value }
    $value = ($value -replace "`r?`n", "<br>")
    $lines += "| $($field.page) | $($field.elementId) | $($field.inputKind) | $(if ($field.required) { 'yes' } else { 'no' }) | $(if ($field.safeForNonLegalDraftSave) { 'yes' } else { 'no' }) | $(if ($field.present) { 'yes' } else { 'no' }) | $($field.label -replace '\|', '/') | $($value -replace '\|', '/') |"
}

$lines += @(
    "",
    "## Safe Next Step",
    "",
    "After Zack confirms, use this payload to save only non-legal public text fields in the Devpost draft. Do not upload files, check legal attestations, or final-submit from this payload.",
    "",
    '```text',
    'Confirm: Codex may save non-legal, non-secret public Project details and Additional info fields to the Devpost draft; no file upload, no legal checkbox, no final submit.',
    '```'
)

Set-Content -Path $payloadMd -Value ($lines -join "`r`n") -Encoding UTF8

if ($readyForFinalDevpostFields) {
    Write-Host "Devpost draft payload READY: $payloadMd"
}
else {
    Write-Host "Devpost draft payload DRAFT: $payloadMd" -ForegroundColor Yellow
    Write-Host "Missing required items: $($requiredFailures.name -join ', ')"
}
Write-Host "JSON: $payloadJson"

if (-not $readyForFinalDevpostFields -and -not $AllowDraft) {
    exit 1
}
