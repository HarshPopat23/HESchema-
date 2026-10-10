/**
 * HESchema — Frontend Client Logic
 * Plain Vanilla JavaScript. Safe text rendering. No external libraries.
 */

(function () {
  "use strict";

  // --- In-Memory State ---
  let apiToken = "";
  let providerRegistry = {};
  let currentDomain = "flights";
  let activeTab = "prompt"; // "prompt" | "benchmark"
  
  // State Confirmation Tracking
  let currentStateId = null;
  let currentStateVersion = null;
  let isStateConfirmed = false;
  let isStateEdited = false;

  // Benchmark Tracking
  let activeJobId = null;
  let jobPollInterval = null;
  let currentReport = null;
  let currentRuns = [];
  let runsPage = 0;
  const RUNS_PER_PAGE = 20;

  // --- DOM Elements ---
  const el = {
    // Auth
    authToggleBtn: document.getElementById("auth-toggle-btn"),
    authBar: document.getElementById("auth-bar"),
    apiTokenInput: document.getElementById("api-token-input"),
    saveTokenBtn: document.getElementById("save-token-btn"),
    tokenStatus: document.getElementById("token-status"),

    // Common Controls
    domainSelect: document.getElementById("domain-select"),
    providerSelect: document.getElementById("provider-select"),
    modelInput: document.getElementById("model-input"),
    schemaEditor: document.getElementById("schema-editor"),
    schemaStatus: document.getElementById("schema-status"),
    schemaError: document.getElementById("schema-error"),
    loadDomainSchemaBtn: document.getElementById("load-domain-schema-btn"),
    uploadSchemaFile: document.getElementById("upload-schema-file"),
    clearSchemaBtn: document.getElementById("clear-schema-btn"),

    // Tabs
    tabBtnPrompt: document.getElementById("tab-btn-prompt"),
    tabBtnBenchmark: document.getElementById("tab-btn-benchmark"),
    tabPrompt: document.getElementById("tab-prompt"),
    tabBenchmark: document.getElementById("tab-benchmark"),

    // Prompt Tab
    promptInput: document.getElementById("prompt-input"),
    loadExampleBtn: document.getElementById("load-example-btn"),
    stateEditor: document.getElementById("state-editor"),
    stateStatusBadge: document.getElementById("state-status-badge"),
    extractStateBtn: document.getElementById("extract-state-btn"),
    confirmStateBtn: document.getElementById("confirm-state-btn"),
    runPromptBtn: document.getElementById("run-prompt-btn"),
    compareArmsBtn: document.getElementById("compare-arms-btn"),
    promptLoading: document.getElementById("prompt-loading-indicator"),

    // Prompt Results
    promptResultsContainer: document.getElementById("prompt-results-container"),
    resultStatusBadge: document.getElementById("result-status-badge"),
    resAction: document.getElementById("res-action"),
    resTool: document.getElementById("res-tool"),
    resLatency: document.getElementById("res-latency"),
    resModel: document.getElementById("res-model"),
    promptValidationTbody: document.getElementById("prompt-validation-tbody"),
    validationErrorsBox: document.getElementById("validation-errors-box"),
    validationErrorsList: document.getElementById("validation-errors-list"),
    resArguments: document.getElementById("res-arguments"),
    resReason: document.getElementById("res-reason"),
    resRawOutput: document.getElementById("res-raw-output"),

    // Single Prompt Compare
    promptCompareContainer: document.getElementById("prompt-compare-container"),
    singleCompareTbody: document.getElementById("single-compare-tbody"),

    // Benchmark Tab
    presetQuickBtn: document.getElementById("preset-quick-btn"),
    presetFullBtn: document.getElementById("preset-full-btn"),
    presetCustomBtn: document.getElementById("preset-custom-btn"),
    customParamsGrid: document.getElementById("custom-params-grid"),
    benchCases: document.getElementById("bench-cases"),
    benchRepeats: document.getElementById("bench-repeats"),
    benchRepairs: document.getElementById("bench-repairs"),
    benchInterval: document.getElementById("bench-interval"),
    benchSeed: document.getElementById("bench-seed"),
    benchInPrice: document.getElementById("bench-in-price"),
    benchOutPrice: document.getElementById("bench-out-price"),
    estimatedCallsCount: document.getElementById("estimated-calls-count"),
    startBenchmarkBtn: document.getElementById("start-benchmark-btn"),
    cancelBenchmarkBtn: document.getElementById("cancel-benchmark-btn"),
    benchStatusIndicator: document.getElementById("bench-status-indicator"),

    // Progress Card
    jobProgressCard: document.getElementById("job-progress-card"),
    jobStatusPill: document.getElementById("job-status-pill"),
    jobProgressBar: document.getElementById("job-progress-bar"),
    progCompleted: document.getElementById("prog-completed"),
    progRequests: document.getElementById("prog-requests"),
    progErrors: document.getElementById("prog-errors"),
    progCurrent: document.getElementById("prog-current"),

    // Report Container
    benchmarkReportContainer: document.getElementById("benchmark-report-container"),
    downloadReportJsonBtn: document.getElementById("download-report-json-btn"),
    downloadReportMdBtn: document.getElementById("download-report-md-btn"),
    downloadRunsJsonlBtn: document.getElementById("download-runs-jsonl-btn"),
    benchmarkWarningsBox: document.getElementById("benchmark-warnings-box"),
    benchmarkArmsTbody: document.getElementById("benchmark-arms-tbody"),
    benchmarkEffectsTbody: document.getElementById("benchmark-effects-tbody"),
    runsArmFilter: document.getElementById("runs-arm-filter"),
    runsTbody: document.getElementById("runs-tbody"),
    runsPagination: document.getElementById("runs-pagination"),

    // Modal
    runDetailModal: document.getElementById("run-detail-modal"),
    modalCloseBtn: document.getElementById("modal-close-btn"),
    modalRunTitle: document.getElementById("modal-run-title"),
    modalPromptView: document.getElementById("modal-prompt-view"),
    modalRawOutput: document.getElementById("modal-raw-output"),
    modalArguments: document.getElementById("modal-arguments"),
    modalErrorsWrap: document.getElementById("modal-errors-wrap"),
    modalStatsWrap: document.getElementById("modal-stats-wrap"),
  };

  // --- HTTP Helper ---
  async function apiFetch(url, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (apiToken) {
      headers["Authorization"] = "Bearer " + apiToken;
    }
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      let errDetail = "Request failed (" + response.status + ")";
      try {
        const errJson = await response.json();
        if (errJson.detail) {
          errDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        } else if (errJson.message) {
          errDetail = errJson.message;
        }
      } catch (e) {
        errDetail = await response.text();
      }
      throw new Error(errDetail || "HTTP Error " + response.status);
    }
    const ct = response.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      return await response.json();
    }
    return await response.text();
  }

  // --- Safe Text Helper ---
  function setSafeText(element, text) {
    element.textContent = text !== null && text !== undefined ? String(text) : "";
  }

  // --- Initialization ---
  async function init() {
    setupEventListeners();
    await loadProviders();
    await loadDomainReferenceSchema(el.domainSelect.value);
    updateCallsEstimate();
  }

  // --- Load Providers ---
  async function loadProviders() {
    try {
      const providers = await apiFetch("/providers");
      providerRegistry = providers;
      el.providerSelect.innerHTML = "";

      const keys = Object.keys(providers);
      keys.forEach((pName) => {
        const opt = document.createElement("option");
        opt.value = pName;
        opt.textContent = pName + " (" + (providers[pName].model || providers[pName].kind) + ")";
        el.providerSelect.appendChild(opt);
      });

      // Default selection priority: groq if available, then mock, then first
      let defaultProvider = keys.includes("groq") ? "groq" : (keys.includes("mock") ? "mock" : keys[0]);
      if (defaultProvider) {
        el.providerSelect.value = defaultProvider;
        syncModelWithProvider(defaultProvider);
      }
    } catch (err) {
      console.error("Failed to load providers:", err);
      el.providerSelect.innerHTML = '<option value="groq">groq (offline fallback)</option>';
      el.modelInput.value = "openai/gpt-oss-20b";
    }
  }

  function syncModelWithProvider(providerName) {
    const pConfig = providerRegistry[providerName];
    if (pConfig && pConfig.model) {
      el.modelInput.value = pConfig.model;
    }
  }

  // --- Load Domain Reference Schema ---
  async function loadDomainReferenceSchema(domain) {
    try {
      const schema = await apiFetch("/schemas/" + encodeURIComponent(domain));
      el.schemaEditor.value = JSON.stringify(schema, null, 2);
      el.schemaStatus.textContent = "Reference schema active (" + domain + ")";
      el.schemaStatus.className = "status-pill status-neutral";
      el.schemaError.classList.add("hidden");
    } catch (err) {
      console.warn("Could not fetch domain reference schema:", err);
    }
  }

  // --- Event Listeners Setup ---
  function setupEventListeners() {
    // Auth Bar Toggle
    el.authToggleBtn.addEventListener("click", () => {
      el.authBar.classList.toggle("hidden");
    });

    el.saveTokenBtn.addEventListener("click", () => {
      apiToken = el.apiTokenInput.value.trim();
      if (apiToken) {
        el.tokenStatus.textContent = "Token stored in memory";
        el.tokenStatus.style.color = "#059669";
      } else {
        el.tokenStatus.textContent = "No token set";
        el.tokenStatus.style.color = "#6b7280";
      }
    });

    // Domain change
    el.domainSelect.addEventListener("change", (e) => {
      currentDomain = e.target.value;
      invalidateCurrentState("Domain changed — previous state invalidated");
      loadDomainReferenceSchema(currentDomain);
      updateCallsEstimate();
    });

    // Provider change
    el.providerSelect.addEventListener("change", (e) => {
      syncModelWithProvider(e.target.value);
    });

    // Schema Actions
    el.loadDomainSchemaBtn.addEventListener("click", () => {
      loadDomainReferenceSchema(el.domainSelect.value);
    });

    el.uploadSchemaFile.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (evt) => {
        try {
          const parsed = JSON.parse(evt.target.result);
          el.schemaEditor.value = JSON.stringify(parsed, null, 2);
          el.schemaStatus.textContent = "Uploaded custom schema";
          el.schemaStatus.className = "status-pill status-running";
          validateSchemaInput();
        } catch (err) {
          showSchemaError("Invalid JSON in uploaded file: " + err.message);
        }
      };
      reader.readAsText(file);
    });

    el.clearSchemaBtn.addEventListener("click", () => {
      el.schemaEditor.value = "";
      el.schemaStatus.textContent = "No custom schema (will use reference)";
      el.schemaStatus.className = "status-pill status-neutral";
      el.schemaError.classList.add("hidden");
    });

    el.schemaEditor.addEventListener("blur", validateSchemaInput);

    // Tab Navigation
    el.tabBtnPrompt.addEventListener("click", () => switchTab("prompt"));
    el.tabBtnBenchmark.addEventListener("click", () => switchTab("benchmark"));

    // Prompt Input change
    el.promptInput.addEventListener("input", () => {
      invalidateCurrentState("Prompt modified — previous state association reset");
    });

    // State Editor change
    el.stateEditor.addEventListener("input", () => {
      if (isStateConfirmed) {
        isStateConfirmed = false;
        isStateEdited = true;
        updateStateStatusBadge("Unconfirmed (edited)", "status-unconfirmed");
      }
    });

    // Load Example
    el.loadExampleBtn.addEventListener("click", loadExampleForDomain);

    // Extract State
    el.extractStateBtn.addEventListener("click", extractProposedState);

    // Confirm State
    el.confirmStateBtn.addEventListener("click", confirmActualState);

    // Run Prompt
    el.runPromptBtn.addEventListener("click", runSinglePrompt);

    // Compare Three Arms
    el.compareArmsBtn.addEventListener("click", compareThreeArmsPrompt);

    // Benchmark Presets
    [el.presetQuickBtn, el.presetFullBtn, el.presetCustomBtn].forEach((btn) => {
      btn.addEventListener("click", () => {
        [el.presetQuickBtn, el.presetFullBtn, el.presetCustomBtn].forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const preset = btn.dataset.preset;
        if (preset === "custom") {
          el.customParamsGrid.classList.remove("hidden");
        } else {
          el.customParamsGrid.classList.add("hidden");
        }
        updateCallsEstimate();
      });
    });

    [el.benchCases, el.benchRepeats, el.benchRepairs].forEach((input) => {
      input.addEventListener("input", updateCallsEstimate);
    });

    // Benchmark Start & Cancel
    el.startBenchmarkBtn.addEventListener("click", startBenchmark);
    el.cancelBenchmarkBtn.addEventListener("click", cancelBenchmark);

    // Runs Filter & Modal
    el.runsArmFilter.addEventListener("change", renderRunsTable);
    el.modalCloseBtn.addEventListener("click", () => el.runDetailModal.classList.add("hidden"));
    el.runDetailModal.addEventListener("click", (e) => {
      if (e.target === el.runDetailModal) el.runDetailModal.classList.add("hidden");
    });
  }

  // --- Tabs Switcher ---
  function switchTab(tab) {
    activeTab = tab;
    if (tab === "prompt") {
      el.tabBtnPrompt.classList.add("active");
      el.tabBtnBenchmark.classList.remove("active");
      el.tabPrompt.classList.add("active");
      el.tabBenchmark.classList.remove("active");
    } else {
      el.tabBtnBenchmark.classList.add("active");
      el.tabBtnPrompt.classList.remove("active");
      el.tabBenchmark.classList.add("active");
      el.tabPrompt.classList.remove("active");
    }
  }

  // --- Schema Validation ---
  async function validateSchemaInput() {
    const raw = el.schemaEditor.value.trim();
    if (!raw) {
      el.schemaError.classList.add("hidden");
      return true;
    }
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      showSchemaError("Malformed JSON: " + err.message);
      return false;
    }

    try {
      const res = await apiFetch("/ui/validate-schema", {
        method: "POST",
        body: JSON.stringify({ schema: parsed, domain: el.domainSelect.value }),
      });
      if (!res.valid) {
        showSchemaError("Invalid Schema: " + res.error);
        return false;
      }
      el.schemaError.classList.add("hidden");
      return true;
    } catch (err) {
      showSchemaError("Validation request failed: " + err.message);
      return false;
    }
  }

  function showSchemaError(msg) {
    el.schemaError.textContent = msg;
    el.schemaError.classList.remove("hidden");
  }

  function getSuppliedSchema() {
    const raw = el.schemaEditor.value.trim();
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  // --- State Confirmation Workflow ---
  function invalidateCurrentState(reason) {
    currentStateId = null;
    currentStateVersion = null;
    isStateConfirmed = false;
    isStateEdited = false;
    updateStateStatusBadge("No state loaded", "status-neutral");
    if (reason) {
      document.getElementById("state-notice").textContent = reason;
    }
  }

  function updateStateStatusBadge(text, className) {
    el.stateStatusBadge.textContent = text;
    el.stateStatusBadge.className = "status-pill " + className;
  }

  async function loadExampleForDomain() {
    const domain = el.domainSelect.value;
    try {
      const ex = await apiFetch("/ui/examples/" + encodeURIComponent(domain));
      el.promptInput.value = ex.prompt;
      el.stateEditor.value = JSON.stringify(ex.state, null, 2);
      currentStateId = null;
      currentStateVersion = null;
      isStateConfirmed = false;
      isStateEdited = false;
      updateStateStatusBadge("Unconfirmed (Example loaded)", "status-unconfirmed");
      document.getElementById("state-notice").textContent = ex.description + " Click 'Confirm Actual State' to verify agreement.";
    } catch (err) {
      alert("Failed to load example: " + err.message);
    }
  }

  async function extractProposedState() {
    const prompt = el.promptInput.value.trim();
    if (!prompt) {
      alert("Enter a prompt first before extracting state.");
      return;
    }
    const domain = el.domainSelect.value;
    const provider = el.providerSelect.value;
    const model = el.modelInput.value.trim() || undefined;

    el.extractStateBtn.disabled = true;
    el.extractStateBtn.textContent = "Extracting...";
    try {
      const res = await apiFetch("/extract", {
        method: "POST",
        body: JSON.stringify({ prompt, domain, provider, model }),
      });
      if (res.state && res.state.state) {
        el.stateEditor.value = JSON.stringify(res.state.state, null, 2);
        currentStateId = res.state.id;
        currentStateVersion = res.state.version;
        isStateConfirmed = false;
        isStateEdited = false;
        updateStateStatusBadge("Unconfirmed proposal (v" + currentStateVersion + ")", "status-unconfirmed");
        document.getElementById("state-notice").textContent = res.notice || "User must inspect values before confirmation.";
      } else {
        const proposal = res.proposal || {};
        const action = proposal.action || "ask_clarification";
        const missing = proposal.missingFields || [];
        const reason = proposal.reason || "Model requested clarification or refused action.";

        if (action === "ask_clarification") {
          const missingStr = missing.length ? missing.join(", ") : "required fields";
          updateStateStatusBadge("Clarification Requested (Missing: " + missingStr + ")", "status-unconfirmed");
          document.getElementById("state-notice").textContent =
            "Model requested clarification: \"" + reason + "\" (Missing: " + missingStr + "). You can fill in the missing fields below and click 'Confirm Actual State' to set an expected state.";

          try {
            const ex = await apiFetch("/ui/examples/" + encodeURIComponent(domain));
            const template = { ...ex.state };
            missing.forEach((f) => {
              if (f in template) template[f] = "<REQUIRED: " + f + ">";
            });
            el.stateEditor.value = JSON.stringify(template, null, 2);
          } catch (e) {
            el.stateEditor.value = JSON.stringify({ action: "ask_clarification", missingFields: missing, reason: reason }, null, 2);
          }
        } else {
          updateStateStatusBadge("Refusal Proposal", "status-unconfirmed");
          document.getElementById("state-notice").textContent =
            "Model refused action: \"" + reason + "\". Policy prohibits this action.";
          el.stateEditor.value = JSON.stringify({ action: "refuse", reason: reason }, null, 2);
        }

        renderPromptResults({
          model: model || el.modelInput.value || "configured model",
          output: JSON.stringify(proposal, null, 2),
          parsed: proposal,
          validation: {
            jsonValid: true,
            actionCorrect: true,
            candidateSchemaValid: true,
            referenceSchemaValid: true,
            semanticChecked: false,
            semanticValid: null,
            policyValid: true,
            result: action === "ask_clarification" ? "CLARIFICATION_REQUESTED" : "REFUSED",
            notice: reason,
            errors: [],
          },
          latencyMs: 0,
          hasConfirmedState: false,
        });
      }
    } catch (err) {
      alert("Extraction failed: " + err.message);
    } finally {
      el.extractStateBtn.disabled = false;
      el.extractStateBtn.textContent = "Extract Proposed State";
    }
  }

  async function confirmActualState() {
    const raw = el.stateEditor.value.trim();
    if (!raw) {
      alert("Enter or extract actual state JSON first.");
      return;
    }
    let parsedState;
    try {
      parsedState = JSON.parse(raw);
    } catch (e) {
      alert("Invalid JSON in state editor: " + e.message);
      return;
    }

    el.confirmStateBtn.disabled = true;
    el.confirmStateBtn.textContent = "Confirming...";

    try {
      let stateRecord;
      if (!currentStateId) {
        // Create state first
        stateRecord = await apiFetch("/states", {
          method: "POST",
          body: JSON.stringify({
            prompt: el.promptInput.value.trim() || "Manual UI test prompt",
            state: parsedState,
          }),
        });
        currentStateId = stateRecord.id;
        currentStateVersion = stateRecord.version;
      } else if (isStateEdited) {
        // Replace modified state
        stateRecord = await apiFetch("/states/" + encodeURIComponent(currentStateId), {
          method: "PUT",
          body: JSON.stringify({
            version: currentStateVersion,
            state: parsedState,
          }),
        });
        currentStateVersion = stateRecord.version;
      }

      // Explicit confirmation
      const confirmed = await apiFetch("/states/" + encodeURIComponent(currentStateId) + "/confirm", {
        method: "POST",
        body: JSON.stringify({ version: currentStateVersion }),
      });

      currentStateVersion = confirmed.version;
      isStateConfirmed = true;
      isStateEdited = false;
      updateStateStatusBadge("Confirmed (v" + currentStateVersion + ")", "status-confirmed");
      document.getElementById("state-notice").textContent = "State confirmed. Ready for semantic validation.";
    } catch (err) {
      alert("Confirmation failed: " + err.message);
    } finally {
      el.confirmStateBtn.disabled = false;
      el.confirmStateBtn.textContent = "Confirm Actual State";
    }
  }

  // --- Workflow 1A: Run Prompt ---
  async function runSinglePrompt() {
    const prompt = el.promptInput.value.trim();
    if (!prompt) {
      alert("Please enter a prompt.");
      return;
    }

    const isValidSchema = await validateSchemaInput();
    if (!isValidSchema) {
      alert("Please fix the schema error before running.");
      return;
    }

    const domain = el.domainSelect.value;
    const provider = el.providerSelect.value;
    const model = el.modelInput.value.trim() || undefined;
    const schemaMode = document.querySelector('input[name="schema-mode"]:checked').value;
    const schema = getSuppliedSchema();

    el.runPromptBtn.disabled = true;
    el.promptLoading.classList.remove("hidden");

    try {
      const payload = {
        prompt,
        domain,
        provider,
        model,
        schemaMode,
        schema,
        stateId: isStateConfirmed ? currentStateId : null,
        stateVersion: isStateConfirmed ? currentStateVersion : null,
      };

      const result = await apiFetch("/ui/prompt-test", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      renderPromptResults(result);
    } catch (err) {
      alert("Generation failed: " + err.message);
    } finally {
      el.runPromptBtn.disabled = false;
      el.promptLoading.classList.add("hidden");
    }
  }

  function renderPromptResults(data) {
    el.promptResultsContainer.classList.remove("hidden");
    const parsed = data.parsed || {};
    const val = data.validation || {};

    // Header Badge
    let badgeClass = "badge-pass";
    let badgeText = val.result || "FAIL";
    if (val.result === "PASS") {
      badgeClass = "badge-pass";
      badgeText = "PASS [VALID & CORRECT]";
    } else if (val.result === "NOT_CHECKED") {
      badgeClass = "badge-uncheck";
      badgeText = "STRUCTURAL CHECK (STATE NOT CONFIRMED)";
    } else if (val.result === "CLARIFICATION_REQUESTED") {
      badgeClass = "badge-uncheck";
      badgeText = "CLARIFICATION REQUESTED (MISSING INFORMATION)";
    } else if (val.result === "REFUSED") {
      badgeClass = "badge-uncheck";
      badgeText = "REQUEST REFUSED (PROHIBITED ACTION)";
    } else {
      badgeClass = "badge-fail";
      badgeText = "FAIL [REJECTED]";
    }
    el.resultStatusBadge.className = "result-badge " + badgeClass;
    setSafeText(el.resultStatusBadge, badgeText);

    // Summary stats
    setSafeText(el.resAction, parsed.action || "None");
    setSafeText(el.resTool, parsed.tool || "None");
    setSafeText(el.resLatency, data.latencyMs ? data.latencyMs.toFixed(1) + " ms" : "—");
    setSafeText(el.resModel, data.model || "—");

    // Validation Table Rows
    const tbody = el.promptValidationTbody;
    tbody.innerHTML = "";

    function addRow(name, status, note, isError) {
      const tr = document.createElement("tr");
      const tdName = document.createElement("td");
      tdName.textContent = name;
      const tdStatus = document.createElement("td");
      tdStatus.textContent = status;
      tdStatus.style.fontWeight = "600";
      tdStatus.style.color = isError ? "#991b1b" : (status === "Not checked" ? "#6b7280" : "#065f46");
      const tdNote = document.createElement("td");
      tdNote.textContent = note;
      tr.appendChild(tdName);
      tr.appendChild(tdStatus);
      tr.appendChild(tdNote);
      tbody.appendChild(tr);
    }

    addRow("Valid Strict JSON", val.jsonValid ? "Yes" : "No", val.jsonValid ? "Parses cleanly" : "Invalid syntax", !val.jsonValid);
    addRow("Output Envelope", val.actionCorrect !== false ? "Valid" : "Invalid", "Envelope matches action/tool contract", val.actionCorrect === false);
    addRow("Candidate Schema Conformance", val.candidateSchemaValid ? "Yes" : "No", "Draft 2020-12 rules", !val.candidateSchemaValid);
    addRow("Reference Contract Conformance", val.referenceSchemaValid ? "Yes" : "No", "Shared benchmark contract", !val.referenceSchemaValid);

    if (val.semanticChecked) {
      addRow(
        "Confirmed State Agreement",
        val.semanticValid ? "Matched" : "Mismatch",
        val.semanticValid ? "All tool arguments match confirmed state" : "Arguments deviate from confirmed values",
        !val.semanticValid
      );
    } else {
      addRow("Confirmed State Agreement", "Not checked", "No confirmed actual state provided", false);
    }

    addRow("Declared Policies", val.policyValid ? "Passed" : "Violated", "Domain boundaries & orderings", !val.policyValid);
    addRow("Execution Authorized", "False", "Project never executes real bookings or payments", false);

    // Errors
    const errors = val.errors || [];
    if (errors.length > 0) {
      el.validationErrorsBox.classList.remove("hidden");
      el.validationErrorsList.innerHTML = "";
      errors.forEach((err) => {
        const li = document.createElement("li");
        li.textContent = typeof err === "object" ? JSON.stringify(err) : String(err);
        el.validationErrorsList.appendChild(li);
      });
    } else {
      el.validationErrorsBox.classList.add("hidden");
    }

    // Arguments and Raw Outputs
    setSafeText(el.resArguments, parsed.arguments ? JSON.stringify(parsed.arguments, null, 2) : "{}");
    const reasonText = (parsed.reason || "") + (parsed.missingFields && parsed.missingFields.length ? "\nMissing Fields: " + JSON.stringify(parsed.missingFields) : "");
    setSafeText(el.resReason, reasonText || "(No reason provided)");
    setSafeText(el.resRawOutput, data.output || "");
  }

  // --- Workflow 1B: Compare Three Arms for Single Prompt ---
  async function compareThreeArmsPrompt() {
    const prompt = el.promptInput.value.trim();
    if (!prompt) {
      alert("Please enter a prompt.");
      return;
    }
    if (!isStateConfirmed || !currentStateId) {
      alert("Comparing three arms requires an independently confirmed actual state.\nPlease click 'Confirm Actual State' first.");
      return;
    }

    const domain = el.domainSelect.value;
    const provider = el.providerSelect.value;
    const model = el.modelInput.value.trim() || undefined;
    const schema = getSuppliedSchema();

    el.compareArmsBtn.disabled = true;
    el.promptLoading.classList.remove("hidden");
    el.promptCompareContainer.classList.add("hidden");

    try {
      const res = await apiFetch("/ui/prompt-compare", {
        method: "POST",
        body: JSON.stringify({
          prompt,
          domain,
          provider,
          model,
          stateId: currentStateId,
          stateVersion: currentStateVersion,
          schema,
          repeats: 1,
        }),
      });

      renderSinglePromptComparison(res);
    } catch (err) {
      alert("Three-arm comparison failed: " + err.message);
    } finally {
      el.compareArmsBtn.disabled = false;
      el.promptLoading.classList.add("hidden");
    }
  }

  function renderSinglePromptComparison(data) {
    el.promptCompareContainer.classList.remove("hidden");
    const tbody = el.singleCompareTbody;
    tbody.innerHTML = "";

    const arms = data.arms || {};
    const armKeys = ["no_schema", "minimal_schema", "input_schema"];

    armKeys.forEach((arm) => {
      const armData = arms[arm];
      if (!armData) return;
      const tr = document.createElement("tr");

      const tdArm = document.createElement("td");
      tdArm.textContent = arm;
      tdArm.style.fontWeight = "600";

      const tdContext = document.createElement("td");
      tdContext.textContent = arm === "no_schema" ? "Prompt-only (no schema)" : (arm === "minimal_schema" ? "Simplified types & required" : "Full supplied schema");

      const tdRate = document.createElement("td");
      tdRate.textContent = armData.successPercent !== undefined ? armData.successPercent.toFixed(1) + "%" : "—";

      const tdLat = document.createElement("td");
      tdLat.textContent = armData.meanLatencyMs ? armData.meanLatencyMs.toFixed(1) + " ms" : "—";

      const firstRun = (armData.runs && armData.runs[0]) || {};
      const tdArgs = document.createElement("td");
      const pre = document.createElement("pre");
      pre.className = "code-block";
      pre.style.maxHeight = "90px";
      pre.textContent = firstRun.parsed && firstRun.parsed.arguments ? JSON.stringify(firstRun.parsed.arguments) : "{}";
      tdArgs.appendChild(pre);

      const tdRes = document.createElement("td");
      const isOk = firstRun.firstPassSuccess;
      tdRes.textContent = isOk ? "PASS" : "FAIL";
      tdRes.style.fontWeight = "700";
      tdRes.style.color = isOk ? "#065f46" : "#991b1b";

      tr.appendChild(tdArm);
      tr.appendChild(tdContext);
      tr.appendChild(tdRate);
      tr.appendChild(tdLat);
      tr.appendChild(tdArgs);
      tr.appendChild(tdRes);
      tbody.appendChild(tr);
    });
  }

  // --- Workflow 2: Schema Benchmark ---
  function getActivePreset() {
    const activeBtn = document.querySelector(".btn-preset.active");
    return activeBtn ? activeBtn.dataset.preset : "quick";
  }

  function updateCallsEstimate() {
    const preset = getActivePreset();
    let cases = 14;
    let repeats = 1;
    let repairs = 0;

    if (preset === "quick") {
      cases = 14;
      repeats = 1;
      repairs = 0;
    } else if (preset === "full") {
      cases = 80;
      repeats = 3;
      repairs = 0;
    } else {
      cases = parseInt(el.benchCases.value, 10) || 14;
      repeats = parseInt(el.benchRepeats.value, 10) || 1;
      repairs = parseInt(el.benchRepairs.value, 10) || 0;
    }

    const initialCalls = cases * 3 * repeats;
    el.estimatedCallsCount.textContent = initialCalls + (repairs > 0 ? " (max " + (initialCalls * (1 + repairs)) + " with repairs)" : "");
  }

  async function startBenchmark() {
    const isValidSchema = await validateSchemaInput();
    if (!isValidSchema) {
      alert("Please fix the argument schema error first.");
      return;
    }

    const domain = el.domainSelect.value;
    const provider = el.providerSelect.value;
    const model = el.modelInput.value.trim() || undefined;
    const preset = getActivePreset();
    const schema = getSuppliedSchema();

    let caseCount = 14;
    let repeats = 1;
    let repairs = 0;
    let interval = 2.5;
    let seed = 42;
    let inputPrice = null;
    let outputPrice = null;

    if (preset === "quick") {
      caseCount = 14;
      repeats = 1;
      repairs = 0;
    } else if (preset === "full") {
      caseCount = 80;
      repeats = 3;
      repairs = 0;
    } else {
      caseCount = parseInt(el.benchCases.value, 10) || 14;
      repeats = parseInt(el.benchRepeats.value, 10) || 1;
      repairs = parseInt(el.benchRepairs.value, 10) || 0;
      interval = parseFloat(el.benchInterval.value) || 2.5;
      seed = parseInt(el.benchSeed.value, 10) || 42;
      inputPrice = el.benchInPrice.value ? parseFloat(el.benchInPrice.value) : null;
      outputPrice = el.benchOutPrice.value ? parseFloat(el.benchOutPrice.value) : null;
    }

    el.startBenchmarkBtn.disabled = true;
    el.cancelBenchmarkBtn.classList.remove("hidden");
    el.benchStatusIndicator.classList.remove("hidden");
    el.jobProgressCard.classList.remove("hidden");
    el.benchmarkReportContainer.classList.add("hidden");

    try {
      const job = await apiFetch("/ui/jobs", {
        method: "POST",
        body: JSON.stringify({
          domain,
          provider,
          model,
          preset,
          caseCount,
          repeats,
          repairs,
          interval,
          seed,
          schema,
          inputPrice,
          outputPrice,
        }),
      });

      activeJobId = job.id;
      pollJobStatus();
    } catch (err) {
      alert("Failed to start benchmark: " + err.message);
      el.startBenchmarkBtn.disabled = false;
      el.cancelBenchmarkBtn.classList.add("hidden");
      el.benchStatusIndicator.classList.add("hidden");
    }
  }

  function pollJobStatus() {
    if (jobPollInterval) clearInterval(jobPollInterval);

    jobPollInterval = setInterval(async () => {
      if (!activeJobId) {
        clearInterval(jobPollInterval);
        return;
      }

      try {
        const job = await apiFetch("/ui/jobs/" + encodeURIComponent(activeJobId));
        updateProgressDisplay(job);

        if (["completed", "failed", "cancelled"].includes(job.status)) {
          clearInterval(jobPollInterval);
          el.startBenchmarkBtn.disabled = false;
          el.cancelBenchmarkBtn.classList.add("hidden");
          el.benchStatusIndicator.classList.add("hidden");

          if (job.status === "completed" || job.status === "cancelled") {
            await loadBenchmarkReport(activeJobId);
          } else if (job.status === "failed") {
            alert("Benchmark job failed: " + (job.error || "Unknown error"));
          }
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    }, 1500);
  }

  function updateProgressDisplay(job) {
    el.jobStatusPill.textContent = job.status.toUpperCase();
    if (job.status === "running") {
      el.jobStatusPill.className = "status-pill status-running";
    } else if (job.status === "completed") {
      el.jobStatusPill.className = "status-pill status-confirmed";
    } else {
      el.jobStatusPill.className = "status-pill status-unconfirmed";
    }

    const p = job.progress || {};
    const total = p.totalScheduled || 1;
    const completed = p.completedRuns || 0;
    const pct = Math.min(100, Math.round((completed / total) * 100));

    el.jobProgressBar.style.width = pct + "%";
    el.progCompleted.textContent = completed + " / " + total + " (" + pct + "%)";
    el.progRequests.textContent = p.requestsAttempted || 0;
    el.progErrors.textContent = p.providerErrors || 0;
    el.progCurrent.textContent = p.currentCase ? p.currentCase + " [" + p.currentArm + "]" : "Scheduling...";
  }

  async function cancelBenchmark() {
    if (!activeJobId) return;
    try {
      await apiFetch("/ui/jobs/" + encodeURIComponent(activeJobId) + "/cancel", { method: "POST" });
      el.jobStatusPill.textContent = "CANCELLING...";
    } catch (err) {
      alert("Cancel request failed: " + err.message);
    }
  }

  // --- Load and Render Benchmark Report ---
  async function loadBenchmarkReport(jobId) {
    try {
      const report = await apiFetch("/ui/jobs/" + encodeURIComponent(jobId) + "/report");
      const runsData = await apiFetch("/ui/jobs/" + encodeURIComponent(jobId) + "/runs?limit=200");
      currentReport = report;
      currentRuns = runsData.runs || [];
      renderBenchmarkReport(report);
      renderRunsTable();
    } catch (err) {
      console.error("Failed to load report:", err);
    }
  }

  function renderBenchmarkReport(report) {
    el.benchmarkReportContainer.classList.remove("hidden");

    // Warnings Box
    const warnings = report.warnings || [];
    el.benchmarkWarningsBox.innerHTML = "";
    if (warnings.length > 0) {
      const ul = document.createElement("ul");
      warnings.forEach((w) => {
        const li = document.createElement("li");
        li.textContent = w;
        ul.appendChild(li);
      });
      el.benchmarkWarningsBox.appendChild(ul);
    }

    // Arms Summary Table
    const armsTbody = el.benchmarkArmsTbody;
    armsTbody.innerHTML = "";
    const arms = report.arms || {};

    ["no_schema", "minimal_schema", "input_schema"].forEach((armName) => {
      const st = arms[armName] || {};
      const tr = document.createElement("tr");

      function td(val) {
        const cell = document.createElement("td");
        cell.textContent = val !== null && val !== undefined ? val : "—";
        return cell;
      }

      const tdArm = document.createElement("td");
      tdArm.textContent = armName;
      tdArm.style.fontWeight = "600";
      tr.appendChild(tdArm);

      tr.appendChild(td(st.firstPassSuccessPercent !== null ? st.firstPassSuccessPercent.toFixed(1) + "%" : "—"));
      tr.appendChild(td(st.finalSuccessPercent !== null ? st.finalSuccessPercent.toFixed(1) + "%" : "—"));
      tr.appendChild(td(st.callSchemaValidityPercent !== null ? st.callSchemaValidityPercent.toFixed(1) + "%" : "—"));
      tr.appendChild(td(st.semanticAccuracyPercent !== null ? st.semanticAccuracyPercent.toFixed(1) + "%" : "—"));
      tr.appendChild(td(st.retryRatePercent !== null ? st.retryRatePercent.toFixed(1) + "%" : "—"));
      tr.appendChild(td(st.providerErrors));
      tr.appendChild(td(st.latencyP50Ms !== null ? st.latencyP50Ms.toFixed(0) + " ms" : "—"));
      tr.appendChild(td(st.latencyP95Ms !== null ? st.latencyP95Ms.toFixed(0) + " ms" : "—"));

      armsTbody.appendChild(tr);
    });

    // Paired Effects Table
    const effectsTbody = el.benchmarkEffectsTbody;
    effectsTbody.innerHTML = "";
    const effects = report.effects || {};

    [
      { key: "versusNoSchema", label: "Input Schema vs No Schema" },
      { key: "versusMinimalSchema", label: "Input Schema vs Minimal Schema" },
    ].forEach((item) => {
      const eff = effects[item.key] || {};
      const tr = document.createElement("tr");

      const tdLabel = document.createElement("td");
      tdLabel.textContent = item.label;
      tdLabel.style.fontWeight = "600";
      tr.appendChild(tdLabel);

      function td(val) {
        const cell = document.createElement("td");
        cell.textContent = val !== null && val !== undefined ? val : "Not available";
        return cell;
      }

      tr.appendChild(td(eff.absoluteUpliftPoints !== null ? eff.absoluteUpliftPoints.toFixed(1) + " pts" : "—"));
      tr.appendChild(td(eff.relativeImprovementPercent !== null ? eff.relativeImprovementPercent.toFixed(1) + "%" : "Not available"));
      tr.appendChild(td(eff.errorReductionPercent !== null ? eff.errorReductionPercent.toFixed(1) + "%" : "Not available"));

      const ciText = eff.confidenceInterval95 ? "[" + eff.confidenceInterval95[0].toFixed(1) + ", " + eff.confidenceInterval95[1].toFixed(1) + "] pts" : "Not available";
      tr.appendChild(td(ciText));

      // Scientific Interpretation rule:
      // If CI crosses zero, effect is Inconclusive regardless of point estimate!
      let interpretation = eff.effect || "inconclusive";
      if (eff.confidenceInterval95 && eff.confidenceInterval95[0] <= 0 && eff.confidenceInterval95[1] >= 0) {
        interpretation = "inconclusive";
      }

      const tdInterp = document.createElement("td");
      tdInterp.textContent = interpretation.toUpperCase();
      tdInterp.style.fontWeight = "700";
      if (interpretation === "improvement") tdInterp.style.color = "#065f46";
      else if (interpretation === "harm") tdInterp.style.color = "#991b1b";
      else tdInterp.style.color = "#92400e";
      tr.appendChild(tdInterp);

      effectsTbody.appendChild(tr);
    });

    // Setup Downloads
    el.downloadReportJsonBtn.onclick = () => downloadFile("/ui/jobs/" + activeJobId + "/report", "report.json");
    el.downloadReportMdBtn.onclick = () => downloadFile("/ui/jobs/" + activeJobId + "/report/markdown", "report.md");
    el.downloadRunsJsonlBtn.onclick = async () => {
      // Download runs.jsonl from backend
      const a = document.createElement("a");
      a.href = "/static/../results/jobs/" + activeJobId + "/runs.jsonl";
      a.download = "runs.jsonl";
      a.click();
    };
  }

  function downloadFile(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.target = "_blank";
    a.click();
  }

  // --- Runs Inspection Table ---
  function renderRunsTable() {
    const tbody = el.runsTbody;
    tbody.innerHTML = "";

    const filter = el.runsArmFilter.value;
    const filtered = filter === "all" ? currentRuns : currentRuns.filter((r) => r.arm === filter);

    const start = runsPage * RUNS_PER_PAGE;
    const pageItems = filtered.slice(start, start + RUNS_PER_PAGE);

    if (pageItems.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#6b7280;">No run records to display</td></tr>';
      return;
    }

    pageItems.forEach((row, idx) => {
      const tr = document.createElement("tr");

      function td(val) {
        const cell = document.createElement("td");
        cell.textContent = val !== null && val !== undefined ? val : "—";
        return cell;
      }

      tr.appendChild(td(row.caseId));
      tr.appendChild(td(row.category));
      tr.appendChild(td(row.arm));
      tr.appendChild(td(row.repeat));

      const isSuccess = row.firstPassSuccess;
      const tdRes = document.createElement("td");
      tdRes.textContent = isSuccess ? "PASS" : "FAIL";
      tdRes.style.fontWeight = "700";
      tdRes.style.color = isSuccess ? "#065f46" : "#991b1b";
      tr.appendChild(tdRes);

      const firstEval = row.firstEvaluation || {};
      tr.appendChild(td(firstEval.candidateSchemaValid ? "Yes" : "No"));
      tr.appendChild(td(firstEval.semanticValid ? "Yes" : "No"));
      tr.appendChild(td(row.latencyMs ? row.latencyMs.toFixed(0) + " ms" : "—"));

      const tdAct = document.createElement("td");
      const btnInspect = document.createElement("button");
      btnInspect.className = "btn btn-sm btn-secondary";
      btnInspect.textContent = "Inspect";
      btnInspect.onclick = () => openRunDetailModal(row);
      tdAct.appendChild(btnInspect);
      tr.appendChild(tdAct);

      tbody.appendChild(tr);
    });

    // Pagination bar
    const totalPages = Math.ceil(filtered.length / RUNS_PER_PAGE);
    el.runsPagination.innerHTML = "";
    if (totalPages > 1) {
      const span = document.createElement("span");
      span.textContent = "Page " + (runsPage + 1) + " of " + totalPages + " (" + filtered.length + " runs)";
      el.runsPagination.appendChild(span);

      const btnGroup = document.createElement("div");
      btnGroup.style.display = "flex";
      btnGroup.style.gap = "6px";

      if (runsPage > 0) {
        const prev = document.createElement("button");
        prev.className = "btn btn-sm btn-secondary";
        prev.textContent = "Prev";
        prev.onclick = () => {
          runsPage--;
          renderRunsTable();
        };
        btnGroup.appendChild(prev);
      }
      if (runsPage < totalPages - 1) {
        const next = document.createElement("button");
        next.className = "btn btn-sm btn-secondary";
        next.textContent = "Next";
        next.onclick = () => {
          runsPage++;
          renderRunsTable();
        };
        btnGroup.appendChild(next);
      }
      el.runsPagination.appendChild(btnGroup);
    }
  }

  // --- Run Inspection Modal ---
  function openRunDetailModal(row) {
    el.modalRunTitle.textContent = "Task: " + row.caseId + " (Arm: " + row.arm + ", Rep: " + row.repeat + ")";

    const firstAttempt = (row.attempts && row.attempts[0]) || {};
    const gen = firstAttempt.generation || {};
    const evalObj = firstAttempt.evaluation || row.firstEvaluation || {};

    // 1. Model-Visible Prompt & Context (hidden gold expected values omitted!)
    const modelContext = "Case: " + row.caseId + "\nCategory: " + row.category + "\nArm: " + row.arm;
    setSafeText(el.modalPromptView, modelContext);

    // 2. Raw Output
    setSafeText(el.modalRawOutput, gen.text || "(Empty output)");

    // 3. Parsed Arguments
    setSafeText(el.modalArguments, evalObj.parsed && evalObj.parsed.arguments ? JSON.stringify(evalObj.parsed.arguments, null, 2) : "{}");

    // 4. Evaluation Errors
    el.modalErrorsWrap.innerHTML = "";
    const errors = evalObj.errors || [];
    if (errors.length > 0) {
      const ul = document.createElement("ul");
      ul.className = "error-box";
      errors.forEach((err) => {
        const li = document.createElement("li");
        li.textContent = typeof err === "object" ? JSON.stringify(err) : String(err);
        ul.appendChild(li);
      });
      el.modalErrorsWrap.appendChild(ul);
    } else {
      const p = document.createElement("p");
      p.textContent = "No validation errors. Passed all gates.";
      p.style.color = "#065f46";
      el.modalErrorsWrap.appendChild(p);
    }

    // 5. Execution & Cost Stats
    el.modalStatsWrap.innerHTML = "";
    function addStat(label, val) {
      const box = document.createElement("div");
      box.className = "stat-box";
      const lbl = document.createElement("span");
      lbl.className = "stat-label";
      lbl.textContent = label;
      const v = document.createElement("span");
      v.className = "stat-val";
      v.textContent = val !== null && val !== undefined ? val : "—";
      box.appendChild(lbl);
      box.appendChild(v);
      el.modalStatsWrap.appendChild(box);
    }

    addStat("Status", row.status);
    addStat("First Pass", row.firstPassSuccess ? "PASS" : "FAIL");
    addStat("Final Success", row.finalSuccess ? "PASS" : "FAIL");
    addStat("Repairs", row.repairAttempts);
    addStat("Latency", row.latencyMs ? row.latencyMs.toFixed(1) + " ms" : "—");
    addStat("Input Tokens", row.inputTokens);
    addStat("Output Tokens", row.outputTokens);
    addStat("Cost", row.costUsd !== null ? "$" + row.costUsd.toFixed(5) : "Not available");

    el.runDetailModal.classList.remove("hidden");
  }

  // --- Run on Load ---
  window.addEventListener("DOMContentLoaded", init);
})();
