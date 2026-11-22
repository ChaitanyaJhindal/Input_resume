"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Upload,
  X,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  Briefcase,
} from "lucide-react";
import {
  UploadBatchResult,
  UploadWithJDResult,
  uploadResumesBatch,
  uploadResumesWithJD,
} from "../lib/api";
import { JobDescription } from "../types/candidate";
import { Button } from "./ui";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: (activatedJdId?: string) => void;
  jds: JobDescription[];
  activeJdId: string | null;
}

type JdMode = "none" | "existing" | "file" | "text";

const ACCEPTED_RESUME_EXTS = new Set([".pdf", ".png", ".jpg", ".jpeg", ".webp"]);
const ACCEPTED_JD_EXTS = new Set([".pdf", ".docx", ".txt", ".md"]);

function hasExtension(name: string, allowed: Set<string>): boolean {
  const lower = name.toLowerCase();
  const idx = lower.lastIndexOf(".");
  return idx >= 0 && allowed.has(lower.slice(idx));
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadComplete,
  jds,
  activeJdId,
}) => {
  const resumeInputRef = useRef<HTMLInputElement | null>(null);
  const jdInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [jdMode, setJdMode] = useState<JdMode>(activeJdId ? "existing" : "none");
  const [chosenJdId, setChosenJdId] = useState<string>(activeJdId || "");
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [jdTitle, setJdTitle] = useState("");
  const [jdText, setJdText] = useState("");

  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<UploadBatchResult | null>(null);
  const [jdBatchResult, setJdBatchResult] = useState<UploadWithJDResult | null>(
    null
  );

  const handleClose = useCallback(() => {
    if (isUploading) return;
    setSelectedFiles([]);
    setJdFile(null);
    setBatchResult(null);
    setJdBatchResult(null);
    setErrorMsg(null);
    onClose();
  }, [isUploading, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, handleClose]);

  if (!isOpen) return null;

  const addResumeFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const valid: File[] = [];
    const rejected: string[] = [];
    Array.from(incoming).forEach((f) => {
      if (hasExtension(f.name, ACCEPTED_RESUME_EXTS)) valid.push(f);
      else rejected.push(f.name);
    });
    if (rejected.length > 0) {
      setErrorMsg(
        `Unsupported resume format skipped (${rejected.join(", ")}). Accepted: PDF, PNG, JPG, WEBP.`
      );
    } else {
      setErrorMsg(null);
    }
    if (valid.length > 0) {
      setSelectedFiles((prev) => {
        const seen = new Set(prev.map((f) => `${f.name}:${f.size}`));
        const next = [...prev];
        for (const f of valid) {
          if (!seen.has(`${f.name}:${f.size}`)) next.push(f);
        }
        return next;
      });
      setBatchResult(null);
      setJdBatchResult(null);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0 || isUploading) return;

    if (jdMode === "existing" && !chosenJdId) {
      setErrorMsg("Select a saved JD or switch JD mode to Baseline / Upload / Paste.");
      return;
    }
    if (jdMode === "file" && !jdFile) {
      setErrorMsg("Attach a Job Description file (.pdf, .docx, .txt, .md).");
      return;
    }
    if (jdMode === "text" && jdText.trim().length < 20) {
      setErrorMsg("Enter at least 20 characters for the Job Description text.");
      return;
    }

    setIsUploading(true);
    setErrorMsg(null);
    try {
      if (jdMode === "none") {
        const res = await uploadResumesBatch(selectedFiles);
        setBatchResult(res);
        setSelectedFiles([]);
        onUploadComplete();
      } else {
        const res = await uploadResumesWithJD({
          files: selectedFiles,
          jdId: jdMode === "existing" ? chosenJdId : undefined,
          jdFile: jdMode === "file" ? jdFile : undefined,
          jdText: jdMode === "text" ? jdText : undefined,
          jdTitle: jdTitle.trim() || undefined,
        });
        setJdBatchResult(res);
        setSelectedFiles([]);
        onUploadComplete(res.jd.jd_id);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const renderedCandidates = jdBatchResult
    ? jdBatchResult.candidates.map((c) => ({
        candidate_id: c.candidate_id,
        name: c.name,
        filename: c.filename,
        scoreLabel: `${c.dynamic_score.toFixed(0)}% JD Fit`,
        tierLabel: c.recommendation_tier.replace(/_/g, " "),
      }))
    : batchResult
    ? batchResult.candidates.map((c) => ({
        candidate_id: c.candidate_id,
        name: c.name,
        filename: c.filename,
        scoreLabel: `${c.overall_score.toFixed(0)}% Rule Score`,
        tierLabel: c.eligibility_status.replace(/_/g, " "),
      }))
    : [];

  const renderedErrors =
    jdBatchResult?.errors ?? batchResult?.errors ?? [];

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 backdrop-blur-xs p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-modal-title"
    >
      <div className="bg-white rounded-lg border border-slate-200/80 shadow-xl w-full max-w-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200/80 flex items-center justify-between gap-3">
          <div>
            <h2
              id="upload-modal-title"
              className="text-sm font-bold text-slate-900"
            >
              Upload Resumes &amp; Target Job Description
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Extracts credentials, PDF academic links (Scholar/ORCID), and evaluates dynamically against your JD
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={isUploading}
            aria-label="Close modal"
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-40 cursor-pointer"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          <div className="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200/80 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                <Briefcase
                  className="w-3.5 h-3.5 text-navy-900"
                  strokeWidth={1.5}
                />
                Target Job Description (Optional)
              </span>
              <div className="inline-flex flex-wrap gap-0.5 p-0.5 rounded-md bg-slate-200/60 border border-slate-200/80">
                {(
                  [
                    { id: "none", label: "Baseline" },
                    { id: "existing", label: "Saved JD" },
                    { id: "file", label: "Upload JD" },
                    { id: "text", label: "Paste JD" },
                  ] as Array<{ id: JdMode; label: string }>
                ).map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setJdMode(m.id)}
                    disabled={m.id === "existing" && jds.length === 0}
                    className={`px-2.5 py-1 text-[11px] font-medium rounded-sm transition cursor-pointer disabled:opacity-40 ${
                      jdMode === m.id
                        ? "bg-navy-900 text-white"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {jdMode === "existing" && (
              <select
                value={chosenJdId}
                onChange={(e) => setChosenJdId(e.target.value)}
                className="w-full px-2.5 py-2 text-xs bg-white border border-slate-200/80 rounded-md focus:outline-none focus:border-navy-900"
              >
                <option value="">Choose saved Job Description...</option>
                {jds.map((j) => (
                  <option key={j.jd_id} value={j.jd_id}>
                    {j.title} {j.department ? `(${j.department})` : ""}
                  </option>
                ))}
              </select>
            )}

            {jdMode === "file" && (
              <div className="space-y-2">
                <input
                  type="text"
                  value={jdTitle}
                  onChange={(e) => setJdTitle(e.target.value)}
                  placeholder="Optional Role Title override..."
                  className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200/80 rounded-md focus:outline-none focus:border-navy-900"
                />
                <div className="flex items-center gap-2">
                  <input
                    ref={jdInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f && hasExtension(f.name, ACCEPTED_JD_EXTS)) {
                        setJdFile(f);
                        setErrorMsg(null);
                      } else if (f) {
                        setErrorMsg("JD file must be PDF, DOCX, TXT, or MD.");
                      }
                      e.target.value = "";
                    }}
                  />
                  <Button
                    variant="secondary"
                    size="xs"
                    onClick={() => jdInputRef.current?.click()}
                  >
                    {jdFile
                      ? "Change JD File"
                      : "Choose JD File (.pdf/.docx/.txt)"}
                  </Button>
                  {jdFile && (
                    <span className="text-xs font-mono text-slate-700 truncate">
                      {jdFile.name}
                    </span>
                  )}
                </div>
              </div>
            )}

            {jdMode === "text" && (
              <div className="space-y-2">
                <input
                  type="text"
                  value={jdTitle}
                  onChange={(e) => setJdTitle(e.target.value)}
                  placeholder="Role Title (e.g., Professor of Practice - Applied AI)..."
                  className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200/80 rounded-md focus:outline-none focus:border-navy-900"
                />
                <textarea
                  rows={4}
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  placeholder="Paste the Job Description requirements, courses, and responsibilities..."
                  className="w-full p-2.5 text-xs bg-white border border-slate-200/80 rounded-md focus:outline-none focus:border-navy-900"
                />
              </div>
            )}
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              addResumeFiles(e.dataTransfer.files);
            }}
            onClick={() => resumeInputRef.current?.click()}
            className={`border border-dashed rounded-lg p-6 text-center cursor-pointer transition ${
              isDragging
                ? "border-navy-900 bg-navy-50/50"
                : "border-slate-300 bg-slate-50/50 hover:border-slate-400 hover:bg-slate-50"
            }`}
          >
            <input
              ref={resumeInputRef}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => {
                addResumeFiles(e.target.files);
                e.target.value = "";
              }}
            />
            <div className="w-10 h-10 rounded-full bg-white border border-slate-200/80 flex items-center justify-center mx-auto mb-3 text-slate-600">
              <Upload className="w-4 h-4" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-slate-800">
              Drop candidate CVs here or click to browse
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports PDF, PNG, JPG, WEBP. Extracts Scholar/ORCID links automatically.
            </p>
          </div>

          {errorMsg && (
            <div className="flex items-start gap-2.5 p-3 rounded-md bg-rose-50 border border-rose-200/80 text-xs text-rose-800">
              <AlertCircle
                className="w-4 h-4 text-rose-600 shrink-0 mt-0.5"
                strokeWidth={1.5}
              />
              <span>{errorMsg}</span>
            </div>
          )}

          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider font-mono tabular-nums">
                Resumes Ready ({selectedFiles.length})
              </div>
              <div className="divide-y divide-slate-200/60 border border-slate-200/80 rounded-lg max-h-36 overflow-y-auto">
                {selectedFiles.map((file, idx) => (
                  <div
                    key={`${file.name}-${file.size}`}
                    className="flex items-center justify-between px-3 py-2 text-xs bg-white"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText
                        className="w-4 h-4 text-navy-900 shrink-0"
                        strokeWidth={1.5}
                      />
                      <span className="font-medium text-slate-800 truncate">
                        {file.name}
                      </span>
                      <span className="text-slate-400 font-mono tabular-nums shrink-0">
                        {(file.size / 1024).toFixed(0)} KB
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedFiles((prev) =>
                          prev.filter((_, i) => i !== idx)
                        )
                      }
                      disabled={isUploading}
                      aria-label={`Remove ${file.name}`}
                      className="text-slate-400 hover:text-rose-600 p-1 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(renderedCandidates.length > 0 || renderedErrors.length > 0) && (
            <div className="space-y-2.5">
              {jdBatchResult && (
                <div className="text-xs font-semibold text-navy-900">
                  Evaluated against JD: {jdBatchResult.jd.title}
                </div>
              )}

              {renderedCandidates.map((cand) => (
                <div
                  key={cand.candidate_id}
                  className="flex items-center justify-between p-2.5 rounded-md bg-white border border-slate-200/80 border-l-2 border-l-emerald-600 text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <CheckCircle2
                      className="w-4 h-4 text-emerald-600 shrink-0"
                      strokeWidth={1.5}
                    />
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-900 truncate">
                        {cand.name}
                      </div>
                      <div className="text-[11px] font-mono text-slate-500 truncate">
                        {cand.filename}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-2">
                    <span className="font-mono font-semibold text-slate-900 tabular-nums">
                      {cand.scoreLabel}
                    </span>
                    <div className="text-[10px] uppercase tracking-wide text-slate-500">
                      {cand.tierLabel}
                    </div>
                  </div>
                </div>
              ))}

              {renderedErrors.map((errItem, idx) => {
                const errFile =
                  errItem.filename || errItem.file || `File ${idx + 1}`;
                return (
                  <div
                    key={`${errFile}-${idx}`}
                    className="flex items-start gap-2 p-2.5 rounded-md bg-rose-50 border border-rose-200/80 text-xs text-rose-800"
                  >
                    <AlertCircle
                      className="w-4 h-4 text-rose-600 shrink-0 mt-0.5"
                      strokeWidth={1.5}
                    />
                    <div>
                      <div className="font-semibold">{errFile}</div>
                      <div className="text-[11px]">{errItem.error}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="px-5 py-3.5 bg-slate-50/70 border-t border-slate-200/80 flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={isUploading}>
            {renderedCandidates.length > 0 ? "Done" : "Cancel"}
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || isUploading}
          >
            {isUploading ? (
              <>
                <Loader2
                  className="w-3.5 h-3.5 animate-spin"
                  strokeWidth={1.5}
                />
                <span className="font-mono tabular-nums">
                  {jdMode === "none" ? "Screening" : "Extracting & Evaluating"} (
                  {selectedFiles.length})...
                </span>
              </>
            ) : (
              <span>
                Run Pipeline{" "}
                {selectedFiles.length > 0 && (
                  <span className="font-mono tabular-nums">
                    ({selectedFiles.length})
                  </span>
                )}
              </span>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};
