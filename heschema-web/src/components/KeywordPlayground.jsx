import React, { useState } from 'react';
import { Play, CheckCircle2, AlertCircle, RefreshCw, FileCode, Check } from 'lucide-react';
import { validateGeneric } from '../utils/heschemaEvaluator';

export default function KeywordPlayground({ keywordData }) {
  const [selectedPresetIndex, setSelectedPresetIndex] = useState(0);
  const currentPreset = keywordData.presets[selectedPresetIndex] || keywordData.presets[0];

  const [schemaStr, setSchemaStr] = useState(JSON.stringify(currentPreset.schema, null, 2));
  const [instanceStr, setInstanceStr] = useState(JSON.stringify(currentPreset.instance, null, 2));
  const [evalResult, setEvalResult] = useState(null);
  const [isCounterexample, setIsCounterexample] = useState(false);

  const handleSelectPreset = (idx) => {
    setSelectedPresetIndex(idx);
    setIsCounterexample(false);
    const p = keywordData.presets[idx];
    setSchemaStr(JSON.stringify(p.schema, null, 2));
    setInstanceStr(JSON.stringify(p.instance, null, 2));
    setEvalResult(null);
  };

  const handleToggleCounterexample = (wantCounter) => {
    setIsCounterexample(wantCounter);
    const p = keywordData.presets[selectedPresetIndex];
    if (wantCounter && p.counterexample) {
      setInstanceStr(JSON.stringify(p.counterexample, null, 2));
    } else {
      setInstanceStr(JSON.stringify(p.instance, null, 2));
    }
    setEvalResult(null);
  };

  const handleRunValidation = () => {
    try {
      const parsedSchema = JSON.parse(schemaStr);
      const parsedInstance = JSON.parse(instanceStr);
      const res = validateGeneric(parsedSchema, parsedInstance);
      setEvalResult(res);
    } catch (e) {
      setEvalResult({ valid: false, errors: [`JSON Parse Error: ${e.message}`] });
    }
  };

  return (
    <div className="keyword-playground-card">
      <div className="playground-header">
        <div className="playground-title-area">
          <FileCode size={18} className="text-primary" />
          <h4 className="playground-title">Interactive {keywordData.name} Playground</h4>
          <span className="badge-vocab">{keywordData.vocabulary}</span>
        </div>

        <div className="playground-controls">
          <label className="preset-label">Preset:</label>
          <select
            className="preset-select"
            value={selectedPresetIndex}
            onChange={(e) => handleSelectPreset(Number(e.target.value))}
          >
            {keywordData.presets.map((preset, idx) => (
              <option key={idx} value={idx}>
                {preset.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="playground-subbar">
        <div className="btn-group">
          <button
            type="button"
            className={`btn-sub ${!isCounterexample ? 'active' : ''}`}
            onClick={() => handleToggleCounterexample(false)}
          >
            <Check size={13} /> Valid Case
          </button>
          <button
            type="button"
            className={`btn-sub ${isCounterexample ? 'active' : ''}`}
            onClick={() => handleToggleCounterexample(true)}
          >
            <AlertCircle size={13} /> Counterexample (Fails)
          </button>
        </div>

        <button type="button" className="btn-run" onClick={handleRunValidation}>
          <Play size={14} /> Run Assertion Check
        </button>
      </div>

      <div className="playground-grid">
        <div className="editor-pane">
          <div className="editor-label">Schema (with `{keywordData.name}`)</div>
          <textarea
            className="code-editor"
            value={schemaStr}
            onChange={(e) => setSchemaStr(e.target.value)}
            rows={8}
            spellCheck="false"
          />
        </div>

        <div className="editor-pane">
          <div className="editor-label">Instance Data (to validate)</div>
          <textarea
            className="code-editor"
            value={instanceStr}
            onChange={(e) => setInstanceStr(e.target.value)}
            rows={8}
            spellCheck="false"
          />
        </div>
      </div>

      {evalResult && (
        <div className={`eval-output-box ${evalResult.valid ? 'output-valid' : 'output-invalid'}`}>
          <div className="eval-status-header">
            {evalResult.valid ? (
              <div className="status-flex success">
                <CheckCircle2 size={18} />
                <span>ASSERTION PASSED: Instance satisfies {keywordData.name} rules</span>
              </div>
            ) : (
              <div className="status-flex failure">
                <AlertCircle size={18} />
                <span>ASSERTION FAILED: Constraints violated</span>
              </div>
            )}
          </div>

          {evalResult.errors && evalResult.errors.length > 0 && (
            <div className="eval-errors-list">
              <span className="error-title">Evaluation Errors:</span>
              <ul>
                {evalResult.errors.map((err, i) => (
                  <li key={i} className="error-item">{err}</li>
                ))}
              </ul>
            </div>
          )}

          {evalResult.logs && evalResult.logs.length > 0 && (
            <div className="eval-logs-list">
              <span className="log-title">Diagnostics & Pointer Trace:</span>
              <ul>
                {evalResult.logs.map((log, i) => (
                  <li key={i} className="log-item">{typeof log === 'string' ? log : JSON.stringify(log)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

