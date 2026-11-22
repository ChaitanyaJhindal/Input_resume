"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Briefcase,
  Plus,
  Upload,
  Play,
  Save,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  Sliders,
} from "lucide-react";
import {
  JDEvaluateStatus,
  JDRequirement,
  JobDescription,
} from "../../types/candidate";
import {
  deleteJD,
  evaluateJD,
  fetchJDEvaluateStatus,
  updateJD,
  uploadJD,
} from "../../lib/api";
import { Button, Card, EmptyState, StatusPill } from "../../components/ui";

interface JDWorkspaceViewProps {
  jds: JobDescription[];
  activeJdId: string | null;
  onSelectActiveJd: (jdId: string | null) => void;
  onRefreshAll: () => Promise<void>;
  onOpenCandidatePool: (jdId: string) => void;
}

export const JDWorkspaceView: React.FC<JDWorkspaceViewProps> = ({
  jds,
  activeJdId,
  onSelectActiveJd,
  onRefreshAll,
  onOpenCandidatePool,
}) => {
  const jdFileRef = useRef<HTMLInputElement | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(
    activeJdId ?? jds[0]?.jd_id ?? null
  );
  const [showCreate, setShowCreate] = useState(jds.length === 0);

  // Create form state
  const [newTitle, setNewTitle] = useState("");
  const [newDept, setNewDept] = useState("");
  const [newText, setNewText] = useState("");
  const [newFile, setNewFile] = useState<File | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Editor state keyed by JD id to avoid synchronous setState in useEffect
  const selectedJd = jds.find((j) => j.jd_id === selectedId) ?? jds[0] ?? null;
  const [editsById, setEditsById] = useState<Record<string, JobDescription>>(
    {}
  );
  const draftJd = selectedJd
    ? editsById[selectedJd.jd_id] ?? selectedJd
    : null;
  const [isSaving, setIsSaving] = useState(false);
  const [evalStatus, setEvalStatus] = useState<JDEvaluateStatus | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [notice, setNotice] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const setDraftJd = (
    updater:
      | JobDescription
      | null
      | ((prev: JobDescription | null) => JobDescription | null)
  ) => {
    if (!selectedJd) return;
    const id = selectedJd.jd_id;
    setEditsById((prev) => {
      const current = prev[id] ?? selectedJd;
      const next = typeof updater === "function" ? updater(current) : updater;
      if (!next) return prev;
      return { ...prev, [id]: next };
    });
  };

  const evalRunning = Boolean(evalStatus?.running);
  const activeEvalJdId = draftJd?.jd_id;
  useEffect(() => {
    if (!evalRunning || !activeEvalJdId) return;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const st = await fetchJDEvaluateStatus(activeEvalJdId);
        if (cancelled) return;
        setEvalStatus(st);
        if (!st.running) {
          setNotice({
            type: "success",
            text: `Evaluated ${st.completed} candidates against '${draftJd?.title}'.`,
          });
          await onRefreshAll();
        }
      } catch {
        // Ignore transient polling hiccup
      }
    }, 1500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [evalRunning, activeEvalJdId, draftJd?.title, onRefreshAll]);

  const handleCreateJd = async () => {
    if (!newFile && newText.trim().length < 20) {
      setNotice({
        type: "error",
        text: "Provide a JD file (.pdf, .docx, .txt) or at least 20 characters of JD text.",
      });
      return;
    }
    setIsCreating(true);
    setNotice(null);
    try {
      const created = await uploadJD({
        file: newFile,
        rawText: newText,
        title: newTitle.trim() || undefined,
        department: newDept.trim() || undefined,
      });
      setNewTitle("");
      setNewDept("");
      setNewText("");
      setNewFile(null);
      setShowCreate(false);
      setSelectedId(created.jd_id);
      onSelectActiveJd(created.jd_id);
      await onRefreshAll();
      setNotice({
        type: "success",
        text: `Parsed JD '${created.title}' (${created.requirements.length} criteria extracted).`,
      });
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to parse JD",
      });
    } finally {
      setIsCreating(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!draftJd) return;
    setIsSaving(true);
    setNotice(null);
    try {
      await updateJD(draftJd.jd_id, {
        title: draftJd.title,
        department: draftJd.department,
        requirements: draftJd.requirements,
        allow_compensating_strengths: draftJd.allow_compensating_strengths,
        weights: draftJd.weights,
      });
      await onRefreshAll();
      setNotice({
        type: "success",
        text: "Updated JD rubric & recalculated scores dynamically.",
      });
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to save JD",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunEvaluation = async () => {
    if (!draftJd) return;
    setNotice(null);
    try {
      const res = await evaluateJD(draftJd.jd_id);
      onSelectActiveJd(draftJd.jd_id);
      if (res.status === "completed") {
        await onRefreshAll();
        setNotice({
          type: "success",
          text: `Evaluated ${res.evaluated_count ?? 0} candidates against '${draftJd.title}'.`,
        });
      } else {
        const st = await fetchJDEvaluateStatus(draftJd.jd_id);
        setEvalStatus(st);
      }
    } catch (err) {
      setNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to start JD evaluation",
      });
    }
  };

  const updateRequirement = (
    idx: number,
    patch: Partial<JDRequirement>
  ) => {
    setDraftJd((prev) =>
      prev
        ? {
            ...prev,
            requirements: prev.requirements.map((r, i) =>
              i === idx ? { ...r, ...patch } : r
            ),
          }
        : prev
    );
  };

  const addRequirement = () => {
    setDraftJd((prev) =>
      prev
        ? {
            ...prev,
            requirements: [
              ...prev.requirements,
              {
                id: `req_${Date.now().toString().slice(-4)}`,
                category: "custom",
                label: "New qualification or competency requirement",
                priority: "strong_preference",
                weight: 1.0,
                strictness: "flexible_with_equivalence",
                jd_quote: null,
              },
            ],
          }
        : prev
    );
  };

  const removeRequirement = (idx: number) => {
    setDraftJd((prev) =>
      prev
        ? {
            ...prev,
            requirements: prev.requirements.filter((_, i) => i !== idx),
          }
        : prev
    );
  };

  const weightSumPct = draftJd
    ? Math.round(
        (draftJd.weights.requirement_fit +
          draftJd.weights.domain_semantic_fit +
          draftJd.weights.teaching_fit +
          draftJd.weights.research_and_impact +
          draftJd.weights.alternative_strength_credit) *
          100
      )
    : 100;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Dynamic Job Descriptions (
            <span className="font-mono tabular-nums">{jds.length}</span>)
          </h2>
          <p className="text-xs text-slate-500">
            Upload any JD to generate custom requirements, weightings, and compensating-strength matching
          </p>
        </div>

        <Button
          variant="primary"
          size="md"
          onClick={() => setShowCreate((v) => !v)}
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={1.5} />
          {showCreate ? "Hide Creator" : "New Job Description"}
        </Button>
      </div>

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

      {showCreate && (
        <Card className="p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-900">
            Parse New Job Description
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Role Title (optional, auto-detected if blank)..."
              className="px-3 py-2 border border-slate-200/80 rounded-md focus:outline-none focus:border-navy-900"
            />
            <input
              type="text"
              value={newDept}
              onChange={(e) => setNewDept(e.target.value)}
              placeholder="Department / School (optional)..."
              className="px-3 py-2 border border-slate-200/80 rounded-md focus:outline-none focus:border-navy-900"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <input
              ref={jdFileRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => {
                setNewFile(e.target.files?.[0] ?? null);
                e.target.value = "";
              }}
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => jdFileRef.current?.click()}
            >
              <Upload className="w-3.5 h-3.5" strokeWidth={1.5} />
              {newFile
                ? newFile.name
                : "Upload JD Document (.pdf / .docx / .txt)"}
            </Button>
            {newFile && (
              <button
                type="button"
                onClick={() => setNewFile(null)}
                className="text-rose-700 hover:underline cursor-pointer"
              >
                Clear file
              </button>
            )}
          </div>

          <textarea
            rows={5}
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            placeholder="Or paste full Job Description text here..."
            className="w-full p-3 text-xs border border-slate-200/80 rounded-md bg-slate-50/70 focus:bg-white focus:outline-none focus:border-navy-900"
          />

          <div className="flex justify-end">
            <Button
              variant="primary"
              size="md"
              onClick={handleCreateJd}
              disabled={isCreating}
            >
              {isCreating ? (
                <>
                  <Loader2
                    className="w-3.5 h-3.5 animate-spin"
                    strokeWidth={1.5}
                  />
                  Parsing JD Rubric...
                </>
              ) : (
                <>
                  <Briefcase className="w-3.5 h-3.5" strokeWidth={1.5} />
                  Create &amp; Extract JD Rubric
                </>
              )}
            </Button>
          </div>
        </Card>
      )}

      {jds.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="w-5 h-5" strokeWidth={1.5} />}
          title="No Job Descriptions Created Yet"
          description="Upload or paste a JD above to unlock holistic per-JD scoring, compensating-strength insights, and dynamic committee approvals."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-3">
            {jds.map((j) => {
              const isSelected = draftJd?.jd_id === j.jd_id;
              const isActive = activeJdId === j.jd_id;
              return (
                <div
                  key={j.jd_id}
                  onClick={() => setSelectedId(j.jd_id)}
                  className={`p-4 rounded-lg border cursor-pointer transition space-y-2.5 bg-white ${
                    isSelected
                      ? "border-navy-900 ring-1 ring-navy-900/20"
                      : "border-slate-200/80 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-slate-900 truncate">
                        {j.title}
                      </div>
                      {j.department && (
                        <div className="text-[11px] text-slate-500 truncate mt-0.5">
                          {j.department}
                        </div>
                      )}
                    </div>
                    {isActive && (
                      <StatusPill variant="navy" className="shrink-0">
                        Active
                      </StatusPill>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span className="px-2 py-0.5 rounded-md border border-slate-200/80 bg-slate-50 text-slate-700 capitalize">
                      {j.role_archetype.replace(/_/g, " ")}
                    </span>
                    <span className="font-mono tabular-nums">
                      {j.requirements.length} criteria &bull;{" "}
                      {j.evaluated_count ?? 0} eval
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {draftJd && (
            <Card className="lg:col-span-2 p-5 space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200/60 pb-4">
                <div className="space-y-1 min-w-0">
                  <h3 className="text-base font-bold text-slate-900">
                    {draftJd.title}
                  </h3>
                  {draftJd.summary && (
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {draftJd.summary}
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onOpenCandidatePool(draftJd.jd_id)}
                  >
                    Ranked Pool
                    <ArrowRight className="w-3.5 h-3.5" strokeWidth={1.5} />
                  </Button>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleRunEvaluation}
                    disabled={evalRunning}
                  >
                    {evalRunning ? (
                      <>
                        <Loader2
                          className="w-3.5 h-3.5 animate-spin"
                          strokeWidth={1.5}
                        />
                        <span className="font-mono tabular-nums">
                          Evaluating {evalStatus?.completed ?? 0}/
                          {evalStatus?.total ?? 0}
                        </span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5" strokeWidth={1.5} />
                        Evaluate All Candidates
                      </>
                    )}
                  </Button>

                  {confirmDeleteId === draftJd.jd_id ? (
                    <div className="inline-flex items-center gap-1">
                      <Button
                        variant="dangerSolid"
                        size="xs"
                        onClick={async () => {
                          await deleteJD(draftJd.jd_id);
                          if (activeJdId === draftJd.jd_id) {
                            onSelectActiveJd(null);
                          }
                          setConfirmDeleteId(null);
                          await onRefreshAll();
                        }}
                      >
                        Confirm
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => setConfirmDeleteId(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => setConfirmDeleteId(draftJd.jd_id)}
                      title="Delete JD"
                      aria-label="Delete JD"
                      className="px-2"
                    >
                      <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                    </Button>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                      <Sliders
                        className="w-3.5 h-3.5 text-navy-900"
                        strokeWidth={1.5}
                      />
                      Dynamic Dimension Weights
                    </span>
                    <StatusPill
                      variant={weightSumPct === 100 ? "neutral" : "amber"}
                      mono
                    >
                      Total: {weightSumPct}%
                      {weightSumPct !== 100 ? " (normalized on save)" : ""}
                    </StatusPill>
                  </div>

                  <label className="inline-flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={draftJd.allow_compensating_strengths}
                      onChange={(e) =>
                        setDraftJd((prev) =>
                          prev
                            ? {
                                ...prev,
                                allow_compensating_strengths: e.target.checked,
                              }
                            : prev
                        )
                      }
                      className="rounded border-slate-300 accent-navy-900"
                    />
                    Credit compensating alternative strengths
                  </label>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 text-xs">
                  {(
                    [
                      { key: "requirement_fit", label: "Requirements" },
                      { key: "domain_semantic_fit", label: "Domain Fit" },
                      { key: "teaching_fit", label: "Teaching" },
                      { key: "research_and_impact", label: "Research" },
                      {
                        key: "alternative_strength_credit",
                        label: "Alt Strengths",
                      },
                    ] as const
                  ).map((dim) => (
                    <label
                      key={dim.key}
                      className="p-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 space-y-2 block"
                    >
                      <div className="flex justify-between items-center font-medium text-slate-700 gap-1">
                        <span className="truncate">{dim.label}</span>
                        <span className="font-mono tabular-nums font-semibold text-navy-900">
                          {Math.round(draftJd.weights[dim.key] * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="0.7"
                        step="0.05"
                        value={draftJd.weights[dim.key]}
                        onChange={(e) =>
                          setDraftJd((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  weights: {
                                    ...prev.weights,
                                    [dim.key]: Number(e.target.value),
                                  },
                                }
                              : prev
                          )
                        }
                        className="navy-slider"
                      />
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                    Extracted Requirements (
                    <span className="font-mono tabular-nums">
                      {draftJd.requirements.length}
                    </span>
                    )
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="xs"
                      onClick={addRequirement}
                    >
                      <Plus className="w-3 h-3" strokeWidth={1.5} />
                      Add Criterion
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleSaveDraft}
                      disabled={isSaving}
                    >
                      <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
                      {isSaving
                        ? "Recalculating..."
                        : "Save Rubric & Recalculate"}
                    </Button>
                  </div>
                </div>

                <div className="divide-y divide-slate-200/60 border border-slate-200/80 rounded-lg overflow-hidden text-xs">
                  {draftJd.requirements.map((req, idx) => (
                    <div
                      key={req.id}
                      className="p-2.5 bg-white flex flex-wrap items-center gap-2"
                    >
                      <input
                        type="text"
                        value={req.label}
                        onChange={(e) =>
                          updateRequirement(idx, { label: e.target.value })
                        }
                        className="flex-1 min-w-[200px] px-2.5 py-1.5 border border-slate-200/80 rounded-md focus:outline-none focus:border-navy-900"
                      />
                      <select
                        value={req.priority}
                        onChange={(e) =>
                          updateRequirement(idx, {
                            priority: e.target.value as JDRequirement["priority"],
                          })
                        }
                        className="px-2 py-1.5 border border-slate-200/80 rounded-md bg-slate-50 text-slate-700 focus:outline-none focus:border-navy-900"
                      >
                        <option value="must_have">Must-Have</option>
                        <option value="strong_preference">Preferred</option>
                        <option value="nice_to_have">Nice-to-Have</option>
                      </select>
                      <select
                        value={req.strictness}
                        onChange={(e) =>
                          updateRequirement(idx, {
                            strictness: e.target
                              .value as JDRequirement["strictness"],
                          })
                        }
                        className="px-2 py-1.5 border border-slate-200/80 rounded-md bg-slate-50 text-slate-700 focus:outline-none focus:border-navy-900"
                      >
                        <option value="flexible_with_equivalence">
                          Flexible w/ Equivalence
                        </option>
                        <option value="strict">Strict</option>
                      </select>
                      <button
                        type="button"
                        onClick={() => removeRequirement(idx)}
                        title="Remove criterion"
                        aria-label={`Remove ${req.label}`}
                        className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
