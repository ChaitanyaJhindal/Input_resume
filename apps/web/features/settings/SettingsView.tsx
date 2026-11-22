"use client";

import React, { useEffect, useState } from "react";
import {
  Save,
  Play,
  Plus,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Server,
} from "lucide-react";
import {
  AppConfigData,
  LlmConfigData,
  PromptTemplateEntry,
  ScreeningRuleConfig,
  ScreeningRulesResponse,
  SystemStatus,
} from "../../types/candidate";
import {
  fetchAppConfig,
  fetchLlmConfig,
  fetchPromptsConfig,
  fetchScreeningRules,
  fetchSystemStatus,
  reloadConfigs,
  triggerRescreen,
  updateAppConfig,
  updateLlmConfig,
  updatePromptsConfig,
  updateScreeningRules,
} from "../../lib/api";
import { Button, Card, UnderlineTabs } from "../../components/ui";

interface SettingsViewProps {
  onSettingsChanged: () => Promise<void>;
}

type SettingsTab = "rules" | "models" | "prompts" | "system";

const RULE_FIELDS = [
  "education.highest_degree",
  "education.highest_institution_category",
  "education.institution_tier",
  "experience.teaching_years",
  "experience.research_years",
  "experience.industry_years",
  "experience.administrative_years",
  "experience.total_years",
  "research.publications_count",
];

const OPERATORS = [
  "==",
  "!=",
  ">=",
  "<=",
  ">",
  "<",
  "in",
  "not_in",
  "contains",
  "regex",
];

const INPUT_CLASS =
  "w-full px-3 py-1.5 text-xs border border-slate-200/80 rounded-md bg-slate-50/70 focus:bg-white focus:outline-none focus:border-navy-900";

const MONO_INPUT_CLASS = `${INPUT_CLASS} font-mono tabular-nums`;

export const SettingsView: React.FC<SettingsViewProps> = ({
  onSettingsChanged,
}) => {
  const [subTab, setSubTab] = useState<SettingsTab>("rules");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isRescreening, setIsRescreening] = useState(false);
  const [preserveManual, setPreserveManual] = useState(true);
  const [notice, setNotice] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const [rules, setRules] = useState<ScreeningRuleConfig[]>([]);
  const [ruleSettings, setRuleSettings] = useState<
    ScreeningRulesResponse["settings"]
  >({
    overall_passing_score_percentage: 70,
    minimum_confidence_for_auto_approval: 0.85,
    needs_review_confidence_floor: 0.65,
  });

  const [llmConfig, setLlmConfig] = useState<LlmConfigData>({});
  const [resolvedModels, setResolvedModels] = useState<Record<string, string>>(
    {}
  );

  const [prompts, setPrompts] = useState<Record<string, PromptTemplateEntry>>(
    {}
  );

  const [appConfig, setAppConfig] = useState<AppConfigData>({});
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadSettings() {
      try {
        const [rulesRes, llmRes, promptsRes, appRes, sysRes] =
          await Promise.all([
            fetchScreeningRules(),
            fetchLlmConfig(),
            fetchPromptsConfig(),
            fetchAppConfig(),
            fetchSystemStatus(),
          ]);
        if (cancelled) return;
        setRules(rulesRes.rules ?? []);
        setRuleSettings(rulesRes.settings);
        setLlmConfig(llmRes.config ?? {});
        setResolvedModels(llmRes.resolved_models ?? {});
        setPrompts(promptsRes.prompts ?? {});
        setAppConfig(appRes ?? {});
        setSystemStatus(sysRes);
      } catch (err) {
        if (!cancelled) {
          setNotice({
            type: "error",
            text:
              err instanceof Error
                ? err.message
                : "Failed to load configuration",
          });
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    loadSettings();
    return () => {
      cancelled = true;
    };
  }, []);

  const showSuccess = (text: string) => setNotice({ type: "success", text });
  const showError = (err: unknown, fallback: string) =>
    setNotice({
      type: "error",
      text: err instanceof Error ? err.message : fallback,
    });

  const handleSaveRules = async () => {
    setIsSaving(true);
    try {
      await updateScreeningRules(rules, ruleSettings);
      showSuccess("Screening rules saved to YAML.");
      await onSettingsChanged();
    } catch (err) {
      showError(err, "Failed to save screening rules");
    } finally {
      setIsSaving(false);
    }
  };

  const handleRescreenAll = async () => {
    setIsRescreening(true);
    try {
      const res = await triggerRescreen(preserveManual);
      showSuccess(res.message);
      await onSettingsChanged();
    } catch (err) {
      showError(err, "Failed to re-screen candidates");
    } finally {
      setIsRescreening(false);
    }
  };

  const handleSaveLlm = async () => {
    setIsSaving(true);
    try {
      const res = await updateLlmConfig(llmConfig);
      setLlmConfig(res.config);
      setResolvedModels(res.resolved_models);
      showSuccess(res.message);
      await onSettingsChanged();
    } catch (err) {
      showError(err, "Failed to update LLM configuration");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSavePrompts = async () => {
    setIsSaving(true);
    try {
      const res = await updatePromptsConfig(prompts);
      setPrompts(res.prompts);
      showSuccess(res.message);
    } catch (err) {
      showError(err, "Failed to update prompt templates");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAppConfig = async () => {
    setIsSaving(true);
    try {
      const res = await updateAppConfig(appConfig);
      setAppConfig(res.config);
      showSuccess(res.message);
      await onSettingsChanged();
    } catch (err) {
      showError(err, "Failed to update pipeline configuration");
    } finally {
      setIsSaving(false);
    }
  };

  const handleHotReload = async () => {
    setIsSaving(true);
    try {
      const res = await reloadConfigs();
      setResolvedModels(res.resolved_models);
      const [rulesRes, llmRes, promptsRes, appRes, sysRes] = await Promise.all([
        fetchScreeningRules(),
        fetchLlmConfig(),
        fetchPromptsConfig(),
        fetchAppConfig(),
        fetchSystemStatus(),
      ]);
      setRules(rulesRes.rules ?? []);
      setRuleSettings(rulesRes.settings);
      setLlmConfig(llmRes.config ?? {});
      setPrompts(promptsRes.prompts ?? {});
      setAppConfig(appRes ?? {});
      setSystemStatus(sysRes);
      showSuccess("Reloaded all YAML configurations from disk.");
      await onSettingsChanged();
    } catch (err) {
      showError(err, "Failed to reload configurations");
    } finally {
      setIsSaving(false);
    }
  };

  const updateRule = (
    idx: number,
    patch: Partial<ScreeningRuleConfig>
  ) => {
    setRules((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, ...patch } : r))
    );
  };

  const formatRequiredValue = (
    val: ScreeningRuleConfig["required_value"]
  ): string => {
    if (Array.isArray(val)) return val.join(", ");
    return String(val ?? "");
  };

  const parseRequiredValue = (
    raw: string,
    operator: string
  ): ScreeningRuleConfig["required_value"] => {
    if (operator === "in" || operator === "not_in") {
      return raw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
    if (
      (operator === ">=" ||
        operator === "<=" ||
        operator === ">" ||
        operator === "<") &&
      raw.trim() !== "" &&
      !Number.isNaN(Number(raw))
    ) {
      return Number(raw);
    }
    return raw;
  };

  if (isLoading) {
    return (
      <Card className="p-8 text-center text-sm text-slate-500">
        Loading YAML configurations...
      </Card>
    );
  }

  const groqModels = llmConfig.groq?.models ?? {};
  const groqDefaults = llmConfig.groq?.defaults ?? {};
  const groqPool = llmConfig.groq?.pool ?? {};
  const jevCfg = llmConfig.jev ?? {};
  const tasksMap = llmConfig.tasks ?? {};

  return (
    <div className="space-y-5">
      <UnderlineTabs
        activeId={subTab}
        onChange={setSubTab}
        items={[
          { id: "rules", label: "Screening Rules", count: rules.length },
          { id: "models", label: "Models & Pool" },
          { id: "prompts", label: "Prompt Templates" },
          { id: "system", label: "Pipeline & System" },
        ]}
        rightSlot={
          <Button
            variant="secondary"
            size="sm"
            onClick={handleHotReload}
            disabled={isSaving}
          >
            <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
            Reload from Disk
          </Button>
        }
      />

      {notice && (
        <Card
          accent={notice.type === "success" ? "emerald" : "rose"}
          className="p-3 text-xs flex items-center gap-2"
        >
          {notice.type === "success" ? (
            <CheckCircle2
              className="w-4 h-4 text-emerald-600 shrink-0"
              strokeWidth={1.5}
            />
          ) : (
            <AlertCircle
              className="w-4 h-4 text-rose-600 shrink-0"
              strokeWidth={1.5}
            />
          )}
          <span className="text-slate-800">{notice.text}</span>
        </Card>
      )}

      {subTab === "rules" && (
        <div className="space-y-5">
          <Card className="p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Global Screening Thresholds
                </h2>
                <p className="text-xs text-slate-500">
                  Controls eligibility cutoffs and automatic approval gates
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <label className="inline-flex items-center gap-1.5 text-xs text-slate-600 mr-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={preserveManual}
                    onChange={(e) => setPreserveManual(e.target.checked)}
                    className="rounded border-slate-300 accent-navy-900"
                  />
                  Preserve manual reviews
                </label>

                <Button
                  variant="navySubtle"
                  size="sm"
                  onClick={handleRescreenAll}
                  disabled={isRescreening}
                >
                  <Play className="w-3.5 h-3.5" strokeWidth={1.5} />
                  {isRescreening
                    ? "Re-Screening..."
                    : "Re-Screen All Candidates"}
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSaveRules}
                  disabled={isSaving}
                >
                  <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
                  Save Rules
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Passing Score Percentage (%)
                </span>
                <input
                  type="number"
                  step="1"
                  value={ruleSettings.overall_passing_score_percentage}
                  onChange={(e) =>
                    setRuleSettings((prev) => ({
                      ...prev,
                      overall_passing_score_percentage: Number(e.target.value),
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Auto-Approve Confidence (0-1)
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={ruleSettings.minimum_confidence_for_auto_approval}
                  onChange={(e) =>
                    setRuleSettings((prev) => ({
                      ...prev,
                      minimum_confidence_for_auto_approval: Number(
                        e.target.value
                      ),
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Needs-Review Floor (0-1)
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={ruleSettings.needs_review_confidence_floor}
                  onChange={(e) =>
                    setRuleSettings((prev) => ({
                      ...prev,
                      needs_review_confidence_floor: Number(e.target.value),
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>
            </div>
          </Card>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                Active Evaluation Rules (
                <span className="font-mono tabular-nums">{rules.length}</span>)
              </h3>
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  setRules((prev) => [
                    ...prev,
                    {
                      id: `RULE_${Date.now().toString().slice(-4)}`,
                      name: "New Screening Rule",
                      field: "experience.teaching_years",
                      operator: ">=",
                      required_value: 2,
                      is_mandatory: false,
                      weight: 10,
                      failure_message: "Requirement not met",
                    },
                  ])
                }
              >
                <Plus className="w-3.5 h-3.5" strokeWidth={1.5} />
                Add Rule
              </Button>
            </div>

            {rules.map((rule, idx) => (
              <Card
                key={`${rule.id}-${idx}`}
                className="p-4 space-y-3 text-xs"
              >
                <div className="grid grid-cols-1 md:grid-cols-6 gap-3 items-end">
                  <label className="block space-y-1 md:col-span-2">
                    <span className="font-semibold text-slate-600">
                      Rule Name
                    </span>
                    <input
                      type="text"
                      value={rule.name}
                      onChange={(e) =>
                        updateRule(idx, { name: e.target.value })
                      }
                      className={INPUT_CLASS}
                    />
                  </label>

                  <label className="block space-y-1 md:col-span-2">
                    <span className="font-semibold text-slate-600">
                      Profile Field
                    </span>
                    <select
                      value={rule.field}
                      onChange={(e) =>
                        updateRule(idx, { field: e.target.value })
                      }
                      className="w-full px-2.5 py-1.5 border border-slate-200/80 rounded-md bg-white focus:outline-none focus:border-navy-900"
                    >
                      {!RULE_FIELDS.includes(rule.field) && (
                        <option value={rule.field}>{rule.field}</option>
                      )}
                      {RULE_FIELDS.map((f) => (
                        <option key={f} value={f}>
                          {f}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="block space-y-1">
                    <span className="font-semibold text-slate-600">
                      Operator
                    </span>
                    <select
                      value={rule.operator}
                      onChange={(e) =>
                        updateRule(idx, { operator: e.target.value })
                      }
                      className="w-full px-2.5 py-1.5 border border-slate-200/80 rounded-md bg-white font-mono focus:outline-none focus:border-navy-900"
                    >
                      {OPERATORS.map((op) => (
                        <option key={op} value={op}>
                          {op}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="block space-y-1">
                    <span className="font-semibold text-slate-600">Weight</span>
                    <input
                      type="number"
                      value={rule.weight}
                      onChange={(e) =>
                        updateRule(idx, { weight: Number(e.target.value) })
                      }
                      className={MONO_INPUT_CLASS}
                    />
                  </label>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-6 gap-3 items-center">
                  <label className="block space-y-1 md:col-span-2">
                    <span className="font-semibold text-slate-600">
                      Required Value{" "}
                      {(rule.operator === "in" ||
                        rule.operator === "not_in") && (
                        <span className="font-normal text-slate-400">
                          (comma-separated)
                        </span>
                      )}
                    </span>
                    <input
                      type="text"
                      value={formatRequiredValue(rule.required_value)}
                      onChange={(e) =>
                        updateRule(idx, {
                          required_value: parseRequiredValue(
                            e.target.value,
                            rule.operator
                          ),
                        })
                      }
                      className={MONO_INPUT_CLASS}
                    />
                  </label>

                  <label className="block space-y-1 md:col-span-2">
                    <span className="font-semibold text-slate-600">
                      Failure Message
                    </span>
                    <input
                      type="text"
                      value={rule.failure_message ?? ""}
                      onChange={(e) =>
                        updateRule(idx, { failure_message: e.target.value })
                      }
                      className={INPUT_CLASS}
                    />
                  </label>

                  <label className="inline-flex items-center gap-2 pt-4 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rule.is_mandatory}
                      onChange={(e) =>
                        updateRule(idx, { is_mandatory: e.target.checked })
                      }
                      className="rounded border-slate-300 accent-navy-900"
                    />
                    <span className="font-semibold text-slate-700">
                      Mandatory
                    </span>
                  </label>

                  <div className="flex justify-end pt-4">
                    <Button
                      variant="danger"
                      size="xs"
                      onClick={() =>
                        setRules((prev) => prev.filter((_, i) => i !== idx))
                      }
                    >
                      <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                      Remove
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {subTab === "models" && (
        <div className="space-y-5">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Groq Model Aliases &amp; API Pool
                </h2>
                <p className="text-xs text-slate-500">
                  Persists to config/llm_config.yaml and hot-reloads active
                  clients
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveLlm}
                disabled={isSaving}
              >
                <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
                Save LLM Config
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              {Object.entries(groqModels).map(([alias, modelId]) => (
                <label key={alias} className="block space-y-1">
                  <span className="font-semibold text-slate-700 capitalize">
                    {alias} Alias
                  </span>
                  <input
                    type="text"
                    value={modelId}
                    onChange={(e) =>
                      setLlmConfig((prev) => ({
                        ...prev,
                        groq: {
                          ...prev.groq,
                          models: {
                            ...prev.groq?.models,
                            [alias]: e.target.value,
                          },
                        },
                      }))
                    }
                    className={MONO_INPUT_CLASS}
                  />
                </label>
              ))}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs pt-3 border-t border-slate-200/60">
              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Default Max Tokens
                </span>
                <input
                  type="number"
                  value={groqDefaults.max_tokens ?? 800}
                  onChange={(e) =>
                    setLlmConfig((prev) => ({
                      ...prev,
                      groq: {
                        ...prev.groq,
                        defaults: {
                          ...prev.groq?.defaults,
                          max_tokens: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Pool Cooldown (s)
                </span>
                <input
                  type="number"
                  step="0.5"
                  value={groqPool.cooldown_seconds ?? 8.0}
                  onChange={(e) =>
                    setLlmConfig((prev) => ({
                      ...prev,
                      groq: {
                        ...prev.groq,
                        pool: {
                          ...prev.groq?.pool,
                          cooldown_seconds: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Max Retries
                </span>
                <input
                  type="number"
                  value={groqPool.max_retries ?? 12}
                  onChange={(e) =>
                    setLlmConfig((prev) => ({
                      ...prev,
                      groq: {
                        ...prev.groq,
                        pool: {
                          ...prev.groq?.pool,
                          max_retries: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Request Timeout (s)
                </span>
                <input
                  type="number"
                  step="1"
                  value={groqPool.request_timeout_seconds ?? 60.0}
                  onChange={(e) =>
                    setLlmConfig((prev) => ({
                      ...prev,
                      groq: {
                        ...prev.groq,
                        pool: {
                          ...prev.groq?.pool,
                          request_timeout_seconds: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  JEV Gate Model
                </span>
                <input
                  type="text"
                  value={jevCfg.model ?? ""}
                  onChange={(e) =>
                    setLlmConfig((prev) => ({
                      ...prev,
                      jev: {
                        ...prev.jev,
                        model: e.target.value,
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1 md:col-span-2">
                <span className="font-semibold text-slate-700">
                  JEV Base URL
                </span>
                <input
                  type="text"
                  value={jevCfg.base_url ?? ""}
                  onChange={(e) =>
                    setLlmConfig((prev) => ({
                      ...prev,
                      jev: {
                        ...prev.jev,
                        base_url: e.target.value,
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  JEV Confidence Threshold
                </span>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={jevCfg.confidence_threshold ?? 0.85}
                  onChange={(e) =>
                    setLlmConfig((prev) => ({
                      ...prev,
                      jev: {
                        ...prev.jev,
                        confidence_threshold: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>
            </div>
          </Card>

          <Card className="p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-900">
              Task-Level Model Routing
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {Object.entries(tasksMap).map(([taskName, cfg]) => (
                <div
                  key={taskName}
                  className="p-3.5 rounded-md bg-slate-50/70 border border-slate-200/80 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-bold text-slate-800">
                      {taskName}
                    </span>
                    <span className="text-[11px] font-mono text-navy-900 truncate">
                      {resolvedModels[taskName] || cfg.model}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <label className="block">
                      <span className="text-[11px] text-slate-500">
                        Model/Alias
                      </span>
                      <input
                        type="text"
                        value={cfg.model ?? ""}
                        onChange={(e) =>
                          setLlmConfig((prev) => ({
                            ...prev,
                            tasks: {
                              ...prev.tasks,
                              [taskName]: { ...cfg, model: e.target.value },
                            },
                          }))
                        }
                        className="w-full mt-0.5 px-2 py-1 border border-slate-200/80 rounded-md bg-white font-mono focus:outline-none focus:border-navy-900"
                      />
                    </label>
                    <label className="block">
                      <span className="text-[11px] text-slate-500">Temp</span>
                      <input
                        type="number"
                        step="0.05"
                        value={cfg.temperature ?? groqDefaults.temperature ?? 0.1}
                        onChange={(e) =>
                          setLlmConfig((prev) => ({
                            ...prev,
                            tasks: {
                              ...prev.tasks,
                              [taskName]: {
                                ...cfg,
                                temperature: Number(e.target.value),
                              },
                            },
                          }))
                        }
                        className="w-full mt-0.5 px-2 py-1 border border-slate-200/80 rounded-md bg-white font-mono tabular-nums focus:outline-none focus:border-navy-900"
                      />
                    </label>
                    <label className="block">
                      <span className="text-[11px] text-slate-500">
                        Max Tokens
                      </span>
                      <input
                        type="number"
                        step="128"
                        value={cfg.max_tokens ?? groqDefaults.max_tokens ?? 800}
                        onChange={(e) =>
                          setLlmConfig((prev) => ({
                            ...prev,
                            tasks: {
                              ...prev.tasks,
                              [taskName]: {
                                ...cfg,
                                max_tokens: Number(e.target.value),
                              },
                            },
                          }))
                        }
                        className="w-full mt-0.5 px-2 py-1 border border-slate-200/80 rounded-md bg-white font-mono tabular-nums focus:outline-none focus:border-navy-900"
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {subTab === "prompts" && (
        <div className="space-y-4">
          <Card className="p-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Configurable Prompt Templates
              </h2>
              <p className="text-xs text-slate-500">
                Persisted to config/prompts.yaml and hot-reloaded across all
                agents
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSavePrompts}
              disabled={isSaving}
            >
              <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
              Save Prompts
            </Button>
          </Card>

          {Object.entries(prompts).map(([sectionKey, entry]) => (
            <Card key={sectionKey} className="p-5 space-y-3 text-xs">
              <h3 className="font-mono font-bold text-sm text-slate-900">
                {sectionKey}
              </h3>

              {Object.entries(entry).map(([fieldKey, fieldValue]) => (
                <label key={fieldKey} className="block space-y-1">
                  <span className="font-mono font-semibold text-slate-600">
                    {fieldKey}
                  </span>
                  <textarea
                    rows={
                      fieldKey === "extraction_instructions" ||
                      fieldKey === "system"
                        ? 8
                        : 4
                    }
                    value={fieldValue}
                    onChange={(e) =>
                      setPrompts((prev) => ({
                        ...prev,
                        [sectionKey]: {
                          ...entry,
                          [fieldKey]: e.target.value,
                        },
                      }))
                    }
                    className="w-full p-2.5 border border-slate-200/80 rounded-md font-mono text-[11px] bg-slate-50/70 focus:bg-white focus:outline-none focus:border-navy-900"
                  />
                </label>
              ))}
            </Card>
          ))}
        </div>
      )}

      {subTab === "system" && (
        <div className="space-y-5">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Pipeline &amp; Review Thresholds
                </h2>
                <p className="text-xs text-slate-500">
                  Persists to config/app_config.yaml
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveAppConfig}
                disabled={isSaving}
              >
                <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
                Save Pipeline Config
              </Button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Vision Render Scale
                </span>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  max="4"
                  value={appConfig.pipeline?.vision_scale ?? 2.0}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      pipeline: {
                        ...prev.pipeline,
                        vision_scale: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Image Quality (1-100)
                </span>
                <input
                  type="number"
                  min="40"
                  max="100"
                  value={appConfig.pipeline?.image_quality ?? 85}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      pipeline: {
                        ...prev.pipeline,
                        image_quality: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Max Pages per Resume
                </span>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={appConfig.pipeline?.max_pages_per_resume ?? 8}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      pipeline: {
                        ...prev.pipeline,
                        max_pages_per_resume: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Max Upload Size (MB)
                </span>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={appConfig.pipeline?.max_upload_size_mb ?? 25}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      pipeline: {
                        ...prev.pipeline,
                        max_upload_size_mb: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  High Confidence Threshold
                </span>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={appConfig.review?.high_confidence_threshold ?? 0.9}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      review: {
                        ...prev.review,
                        high_confidence_threshold: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Review Queue Confidence
                </span>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={appConfig.review?.queue_confidence_threshold ?? 0.85}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      review: {
                        ...prev.review,
                        queue_confidence_threshold: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Min Teaching Flag (yrs)
                </span>
                <input
                  type="number"
                  step="0.5"
                  value={appConfig.review?.queue_min_teaching_years ?? 2.0}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      review: {
                        ...prev.review,
                        queue_min_teaching_years: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>

              <label className="block space-y-1">
                <span className="font-semibold text-slate-700">
                  Batch Upload Delay (s)
                </span>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={appConfig.pipeline?.batch_upload_delay_seconds ?? 0.3}
                  onChange={(e) =>
                    setAppConfig((prev) => ({
                      ...prev,
                      pipeline: {
                        ...prev.pipeline,
                        batch_upload_delay_seconds: Number(e.target.value),
                      },
                    }))
                  }
                  className={MONO_INPUT_CLASS}
                />
              </label>
            </div>
          </Card>

          {systemStatus && (
            <Card className="p-5 space-y-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Server className="w-4 h-4 text-navy-900" strokeWidth={1.5} />
                Live Runtime Diagnostics
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80 flex justify-between">
                  <span className="text-slate-500">Environment / Mode</span>
                  <span className="font-mono tabular-nums font-semibold text-slate-800">
                    {systemStatus.environment} &bull;{" "}
                    {systemStatus.mock_mode ? "Mock" : "Live Groq"}
                  </span>
                </div>
                <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80 flex justify-between">
                  <span className="text-slate-500">Groq Keys Loaded</span>
                  <span className="font-mono tabular-nums font-semibold text-slate-800">
                    {systemStatus.groq_keys_count} keys
                  </span>
                </div>
                <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80 flex justify-between gap-2">
                  <span className="text-slate-500 shrink-0">
                    Source Folder
                  </span>
                  <span className="font-mono text-slate-800 truncate">
                    {systemStatus.resumes_directory}
                  </span>
                </div>
                <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80 flex justify-between gap-2">
                  <span className="text-slate-500 shrink-0">Database</span>
                  <span className="font-mono text-slate-800 truncate">
                    {systemStatus.database}
                  </span>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
