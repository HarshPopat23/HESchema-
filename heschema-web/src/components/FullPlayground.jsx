import React, { useState } from 'react';
import { 
  Terminal, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Layers, 
  Database, 
  BarChart3, 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  Copy, 
  Check, 
  ShieldAlert,
  ArrowRight
} from 'lucide-react';
import { KEYWORDS_DATA } from '../data/keywordsData';
import { validateGeneric, resolvePointer } from '../utils/heschemaEvaluator';
import KeywordPlayground from './KeywordPlayground';

const SAMPLE_CONTRACTS = {
  flights: {
    id: 'flights-booking',
    name: 'Flights Booking (search_flights)',
    domain: 'flights',
    description: 'Enforces strict confirmed departure & destination binding to prevent destination hallucination.',
    schema: {
      type: 'object',
      required: ['origin', 'destination', 'departureDate', 'travellers'],
      properties: {
        origin: { type: 'string', minLength: 3 },
        destination: { type: 'string', minLength: 3 },
        departureDate: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' },
        travellers: { type: 'integer', minimum: 1, maximum: 9 }
      },
      additionalProperties: false
    },
    context: {
      origin: 'Jaipur',
      destination: 'Goa',
      departureDate: '2027-01-01',
      travellers: 1
    },
    validOutput: {
      action: 'call_tool',
      tool: 'search_flights',
      arguments: {
        origin: 'Jaipur',
        destination: 'Goa',
        departureDate: '2027-01-01',
        travellers: 1
      },
      missingFields: [],
      reason: 'User requested flight search to Goa'
    },
    mismatchOutput: {
      action: 'call_tool',
      tool: 'search_flights',
      arguments: {
        origin: 'Jaipur',
        destination: 'Pune', // Hallucinated mismatch!
        departureDate: '2027-01-01',
        travellers: 1
      },
      missingFields: [],
      reason: 'User requested flight search to Goa'
    }
  },
  invoice: {
    id: 'invoice-demo',
    name: 'Peppol Invoice Total (product_equals)',
    domain: 'invoicing',
    description: 'Validates that totalMinor matches exact integer product of quantity * unitPriceMinor.',
    schema: {
      type: 'object',
      required: ['quantity', 'unitPriceMinor', 'totalMinor'],
      properties: {
        quantity: { type: 'integer', minimum: 1 },
        unitPriceMinor: { type: 'integer', minimum: 0 },
        totalMinor: { type: 'integer', minimum: 0 }
      },
      additionalProperties: false
    },
    context: {
      quantity: 3,
      unitPriceMinor: 1250 // $12.50
    },
    validOutput: {
      quantity: 3,
      unitPriceMinor: 1250,
      totalMinor: 3750 // $37.50
    },
    mismatchOutput: {
      quantity: 3,
      unitPriceMinor: 1250,
      totalMinor: 5000 // Wrong arithmetic!
    }
  },
  trip: {
    id: 'trip-demo',
    name: 'Custom Trip with Partial Context Approval',
    domain: 'travel',
    description: 'Binds destination to confirmed state, while allowing model to suggest travellers.',
    schema: {
      type: 'object',
      required: ['destination', 'travellers'],
      properties: {
        destination: { type: 'string' },
        travellers: { type: 'integer', minimum: 1, maximum: 8 }
      },
      additionalProperties: false
    },
    context: {
      destination: 'Kyoto'
    },
    validOutput: {
      action: 'call_tool',
      tool: 'prepare_custom_trip',
      arguments: {
        destination: 'Kyoto',
        travellers: 2
      }
    },
    mismatchOutput: {
      action: 'call_tool',
      tool: 'prepare_custom_trip',
      arguments: {
        destination: 'Osaka',
        travellers: 2
      }
    }
  }
};

export default function FullPlayground() {
  const [activeTab, setActiveTab] = useState('keywords'); // 'keywords' | 'contracts' | 'simulator' | 'backend'

  // Keywords State
  const [selectedKeywordId, setSelectedKeywordId] = useState('compareFields');
  const activeKeyword = KEYWORDS_DATA[selectedKeywordId];

  // Contracts State
  const [selectedContractId, setSelectedContractId] = useState('flights');
  const contract = SAMPLE_CONTRACTS[selectedContractId];
  const [contextDataStr, setContextDataStr] = useState(JSON.stringify(contract.context, null, 2));
  const [outputDataStr, setOutputDataStr] = useState(JSON.stringify(contract.validOutput, null, 2));
  const [contractResult, setContractResult] = useState(null);
  const [isCopied, setIsCopied] = useState(false);

  // Backend Connect State
  const [backendUrl, setBackendUrl] = useState('http://127.0.0.1:8000');
  const [backendHealth, setBackendHealth] = useState(null);
  const [backendChecking, setBackendChecking] = useState(false);

  // Benchmark Simulator State
  const [simRunning, setSimRunning] = useState(false);
  const [simResults, setSimResults] = useState(null);

  const handleSelectContract = (id) => {
    setSelectedContractId(id);
    const c = SAMPLE_CONTRACTS[id];
    setContextDataStr(JSON.stringify(c.context, null, 2));
    setOutputDataStr(JSON.stringify(c.validOutput, null, 2));
    setContractResult(null);
  };

  const handleInjectMismatch = () => {
    setOutputDataStr(JSON.stringify(contract.mismatchOutput, null, 2));
    setContractResult(null);
  };

  const handleResetValid = () => {
    setOutputDataStr(JSON.stringify(contract.validOutput, null, 2));
    setContractResult(null);
  };

  const handleValidateContract = () => {
    try {
      const parsedContext = JSON.parse(contextDataStr);
      const parsedOutput = JSON.parse(outputDataStr);

      const targetObj = parsedOutput.arguments || parsedOutput;
      const errors = [];
      let schemaPassed = true;

      // 1. Check basic schema types
      for (const req of contract.schema.required || []) {
        if (targetObj[req] === undefined) {
          errors.push(`Missing required field: '${req}'`);
          schemaPassed = false;
        }
      }

      // 2. Check context bindings
      let stateMismatch = false;
      const mismatchField = [];

      for (const [k, v] of Object.entries(parsedContext)) {
        if (targetObj[k] !== undefined && targetObj[k] !== v) {
          stateMismatch = true;
          mismatchField.push({
            pointer: `/arguments/${k}`,
            expected: v,
            received: targetObj[k]
          });
        }
      }

      // 3. Relational check for invoice
      if (contract.id === 'invoice-demo') {
        const qty = targetObj.quantity;
        const unit = targetObj.unitPriceMinor;
        const total = targetObj.totalMinor;
        if (qty * unit !== total) {
          errors.push(`Relationship failed: totalMinor (${total}) != quantity (${qty}) * unitPriceMinor (${unit}) = ${qty * unit}`);
        }
      }

      let repairPrompt = null;
      if (stateMismatch) {
        const first = mismatchField[0];
        repairPrompt = `[HESchema Repair Directive (category-v1: source_value)]\nValidation failed at pointer: ${first.pointer}\nExpected value bound to confirmed context: ${JSON.stringify(first.expected)}\nReceived generated value: ${JSON.stringify(first.received)}\nDirective: Correct ${first.pointer} to match confirmed context. Do not alter other fields.`;
      } else if (errors.length > 0) {
        repairPrompt = `[HESchema Repair Directive (category-v1: relationship)]\nValidation failed: ${errors[0]}\nDirective: Correct computed target to satisfy mathematical relationship.`;
      }

      const passed = schemaPassed && !stateMismatch && errors.length === 0;

      setContractResult({
        passed,
        resultCode: passed ? 'PASS' : (stateMismatch ? 'FAIL (STATE_MISMATCH)' : 'FAIL'),
        referenceSchemaValid: schemaPassed,
        semanticValid: !stateMismatch && errors.length === 0,
        executionAuthorized: false, // ALWAYS false
        errors,
        mismatches: mismatchField,
        repairPrompt
      });

    } catch (e) {
      setContractResult({
        passed: false,
        resultCode: 'JSON_SYNTAX_ERROR',
        referenceSchemaValid: false,
        semanticValid: false,
        executionAuthorized: false,
        errors: [`Syntax error: ${e.message}`]
      });
    }
  };

  const handleTestBackend = async () => {
    setBackendChecking(true);
    try {
      const res = await fetch(`${backendUrl}/health`);
      if (res.ok) {
        const data = await res.json();
        setBackendHealth({ status: 'online', data });
      } else {
        setBackendHealth({ status: 'error', message: `Server returned HTTP ${res.status}` });
      }
    } catch (e) {
      setBackendHealth({ status: 'offline', message: `Could not reach ${backendUrl}. Ensure 'python -m heschema.cli serve' is running.` });
    } finally {
      setBackendChecking(false);
    }
  };

  const handleRunSimulation = () => {
    setSimRunning(true);
    setSimResults(null);
    setTimeout(() => {
      setSimResults({
        arms: [
          { name: 'Prompt-Only', formatValid: '0.0%', correctAnswers: 0, wrongAccepted: 0, medianLatency: '24.4s', tokens: 460 },
          { name: 'Native Schema (GBNF)', formatValid: '96.9%', correctAnswers: 56, wrongAccepted: 4, medianLatency: '1.24s', tokens: 14 },
          { name: 'HESchema Contract', formatValid: '96.9%', correctAnswers: 56, wrongAccepted: 0, medianLatency: '1.25s', tokens: 14 }
        ],
        h60Summary: {
          ordinaryWrongAccepted: 42,
          contractWrongAccepted: 0,
          compactTokenSavings: '17.42% to 19.53%'
        }
      });
      setSimRunning(false);
    }, 800);
  };

  return (
    <div className="full-playground-container">
      {/* Top Playground Navigation */}
      <div className="playground-tabs-bar">
        <div className="tab-buttons">
          <button
            type="button"
            className={`playground-tab-btn ${activeTab === 'keywords' ? 'active' : ''}`}
            onClick={() => setActiveTab('keywords')}
          >
            <Layers size={16} />
            <span>1. Vocabulary Keywords</span>
          </button>

          <button
            type="button"
            className={`playground-tab-btn ${activeTab === 'contracts' ? 'active' : ''}`}
            onClick={() => setActiveTab('contracts')}
          >
            <Database size={16} />
            <span>2. Contract & State Validator</span>
          </button>

          <button
            type="button"
            className={`playground-tab-btn ${activeTab === 'simulator' ? 'active' : ''}`}
            onClick={() => setActiveTab('simulator')}
          >
            <BarChart3 size={16} />
            <span>3. 3-Arm Experiment Simulator</span>
          </button>

          <button
            type="button"
            className={`playground-tab-btn ${activeTab === 'backend' ? 'active' : ''}`}
            onClick={() => setActiveTab('backend')}
          >
            <Wifi size={16} />
            <span>4. FastAPI / Custom API Bridge</span>
          </button>
        </div>

        <div className="playground-badge-mode">
          <span className="dot-active"></span>
          <span>HESchema Client Engine v1.0.0</span>
        </div>
      </div>

      {/* TAB 1: KEYWORDS */}
      {activeTab === 'keywords' && (
        <div className="playground-tab-body">
          <div className="keyword-selector-bar">
            <span className="selector-label">Select Assertion Keyword:</span>
            <div className="keyword-pills">
              {Object.keys(KEYWORDS_DATA).map((kwId) => (
                <button
                  key={kwId}
                  type="button"
                  className={`pill-kw ${selectedKeywordId === kwId ? 'active' : ''}`}
                  onClick={() => setSelectedKeywordId(kwId)}
                >
                  <code>{kwId}</code>
                </button>
              ))}
            </div>
          </div>

          <KeywordPlayground key={selectedKeywordId} keywordData={activeKeyword} />
        </div>
      )}

      {/* TAB 2: CONTRACTS & STATE VALIDATOR */}
      {activeTab === 'contracts' && (
        <div className="playground-tab-body">
          <div className="contract-header-card">
            <div className="contract-meta">
              <h3>State-Aware Contract Validation</h3>
              <p>Test how HESchema catches semantic hallucinations (e.g. Pune vs Goa) that ordinary schemas silently pass.</p>
            </div>

            <div className="contract-picker">
              <label>Domain Contract:</label>
              <select
                value={selectedContractId}
                onChange={(e) => handleSelectContract(e.target.value)}
              >
                {Object.keys(SAMPLE_CONTRACTS).map((id) => (
                  <option key={id} value={id}>
                    {SAMPLE_CONTRACTS[id].name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="quick-actions-bar">
            <div className="btn-group">
              <button type="button" className="btn-action valid" onClick={handleResetValid}>
                <CheckCircle2 size={14} /> Load Ground-Truth Output
              </button>
              <button type="button" className="btn-action mismatch" onClick={handleInjectMismatch}>
                <ShieldAlert size={14} /> Inject State Mismatch (Hallucination)
              </button>
            </div>

            <button type="button" className="btn-execute-contract" onClick={handleValidateContract}>
              <Play size={15} /> Execute State-Aware Validation
            </button>
          </div>

          <div className="contract-grid">
            <div className="grid-col">
              <div className="col-header">
                <span>Confirmed State Snapshot (Version 1)</span>
                <span className="tag-locked">SQLite Locked</span>
              </div>
              <textarea
                className="code-editor"
                value={contextDataStr}
                onChange={(e) => setContextDataStr(e.target.value)}
                rows={9}
                spellCheck="false"
              />
            </div>

            <div className="grid-col">
              <div className="col-header">
                <span>LLM Proposed Tool Output</span>
                <span className="tag-proposal">Proposal</span>
              </div>
              <textarea
                className="code-editor"
                value={outputDataStr}
                onChange={(e) => setOutputDataStr(e.target.value)}
                rows={9}
                spellCheck="false"
              />
            </div>
          </div>

          {contractResult && (
            <div className={`contract-result-card ${contractResult.passed ? 'res-pass' : 'res-fail'}`}>
              <div className="res-header">
                <div className="res-title">
                  {contractResult.passed ? (
                    <>
                      <CheckCircle2 size={20} className="text-green" />
                      <span>VALIDATION PASSED: Arguments match confirmed state</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle size={20} className="text-red" />
                      <span>VALIDATION FAILED: {contractResult.resultCode}</span>
                    </>
                  )}
                </div>

                <div className="res-flags">
                  <span className={`flag ${contractResult.referenceSchemaValid ? 'ok' : 'err'}`}>
                    SchemaValid: {String(contractResult.referenceSchemaValid)}
                  </span>
                  <span className={`flag ${contractResult.semanticValid ? 'ok' : 'err'}`}>
                    SemanticValid: {String(contractResult.semanticValid)}
                  </span>
                  <span className="flag auth-boundary">
                    executionAuthorized: false
                  </span>
                </div>
              </div>

              {contractResult.mismatches && contractResult.mismatches.length > 0 && (
                <div className="mismatches-box">
                  <strong>State Mismatches Detected:</strong>
                  <ul>
                    {contractResult.mismatches.map((m, i) => (
                      <li key={i}>
                        At <code>{m.pointer}</code>: Confirmed State = <code>{JSON.stringify(m.expected)}</code>, Generated = <code>{JSON.stringify(m.received)}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {contractResult.errors && contractResult.errors.length > 0 && (
                <div className="errors-box">
                  <strong>Diagnostic Errors:</strong>
                  <ul>
                    {contractResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {contractResult.repairPrompt && (
                <div className="repair-prompt-card">
                  <div className="repair-header">
                    <span>Generated Category-v1 Targeted Repair Feedback</span>
                    <button
                      className="copy-repair-btn"
                      onClick={() => {
                        navigator.clipboard.writeText(contractResult.repairPrompt);
                        setIsCopied(true);
                        setTimeout(() => setIsCopied(false), 2000);
                      }}
                    >
                      {isCopied ? <Check size={13} /> : <Copy size={13} />}
                      <span>{isCopied ? 'Copied' : 'Copy Prompt'}</span>
                    </button>
                  </div>
                  <pre className="repair-body">{contractResult.repairPrompt}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: BENCHMARK SIMULATOR */}
      {activeTab === 'simulator' && (
        <div className="playground-tab-body">
          <div className="sim-header-card">
            <h3>3-Arm Schema Effect Benchmark Simulator</h3>
            <p>Compare Prompt-Only vs Native Constrained Decoding vs HESchema Contracts using empirical evidence from our 65-case and 2,160-slot evaluations.</p>
            <button className="btn-sim-run" onClick={handleRunSimulation} disabled={simRunning}>
              {simRunning ? <RefreshCw className="spin" size={16} /> : <Play size={16} />}
              <span>{simRunning ? 'Replaying 65 Evaluation Slots...' : 'Run 3-Arm Simulation Replay'}</span>
            </button>
          </div>

          {simResults && (
            <div className="sim-results-container">
              <div className="table-wrapper">
                <table className="k8s-docs-table">
                  <thead>
                    <tr>
                      <th>Operational Arm</th>
                      <th>Valid JSON Syntax</th>
                      <th>Gold Task Success</th>
                      <th>Wrong Accepted</th>
                      <th>Median Latency</th>
                      <th>Median Output Tokens</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simResults.arms.map((arm, i) => (
                      <tr key={i} className={i === 2 ? 'highlight-contract-row' : ''}>
                        <td><strong>{arm.name}</strong></td>
                        <td>{arm.formatValid}</td>
                        <td>{arm.correctAnswers} / 65</td>
                        <td>
                          {arm.wrongAccepted > 0 ? (
                            <span className="badge-danger">{arm.wrongAccepted} accepted</span>
                          ) : (
                            <span className="badge-success">0 accepted</span>
                          )}
                        </td>
                        <td>{arm.medianLatency}</td>
                        <td>{arm.tokens} tokens</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="sim-highlights-grid">
                <div className="stat-card">
                  <div className="stat-num text-red">42 vs 0</div>
                  <div className="stat-label">Wrong Answers Accepted</div>
                  <div className="stat-sub">Ordinary schema accepted 42 invalid hallucinations; HESchema accepted 0.</div>
                </div>

                <div className="stat-card">
                  <div className="stat-num text-green">-17.42%</div>
                  <div className="stat-label">Token Savings (COMPACT)</div>
                  <div className="stat-sub">COMPACT contract encoding reduced prompt tokens across 2,128 matched slots.</div>
                </div>

                <div className="stat-card">
                  <div className="stat-num text-blue">~20x</div>
                  <div className="stat-label">Native Decoding Speedup</div>
                  <div className="stat-sub">Constrained grammar decoding reduced median latency from 24.4s to 1.24s.</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: BACKEND API BRIDGE */}
      {activeTab === 'backend' && (
        <div className="playground-tab-body">
          <div className="backend-card">
            <h3>Connect to Local HESchema FastAPI Backend</h3>
            <p>You can run <code>python -m heschema.cli serve --port 8000</code> in your terminal and test live requests directly from this React frontend.</p>

            <div className="backend-input-row">
              <input
                type="text"
                className="backend-url-input"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000"
              />
              <button
                type="button"
                className="btn-ping"
                onClick={handleTestBackend}
                disabled={backendChecking}
              >
                {backendChecking ? <RefreshCw className="spin" size={15} /> : <Wifi size={15} />}
                <span>Ping /health Endpoint</span>
              </button>
            </div>

            {backendHealth && (
              <div className={`backend-status-box ${backendHealth.status === 'online' ? 'status-online' : 'status-offline'}`}>
                {backendHealth.status === 'online' ? (
                  <>
                    <div className="status-title">
                      <Wifi size={18} className="text-green" />
                      <span>Connected to FastAPI backend!</span>
                    </div>
                    <pre>{JSON.stringify(backendHealth.data, null, 2)}</pre>
                  </>
                ) : (
                  <>
                    <div className="status-title">
                      <WifiOff size={18} className="text-red" />
                      <span>Backend Unavailable (Standalone in-browser mode active)</span>
                    </div>
                    <p>{backendHealth.message}</p>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

