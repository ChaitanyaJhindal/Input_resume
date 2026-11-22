"use client";

import React from "react";
import { BookOpen, FileText, ShieldCheck } from "lucide-react";
import {
  Candidate,
  PublicationEntry,
  ResearchProjectEntry,
  ResumeResultResponse,
} from "../../../types/candidate";
import { Card, CardHeader, StatusPill } from "../../../components/ui";

interface ResearchTabProps {
  researchDomains: string[];
  publications: PublicationEntry[];
  researchProjects: ResearchProjectEntry[];
}

export const ResearchTab: React.FC<ResearchTabProps> = ({
  researchDomains,
  publications,
  researchProjects,
}) => {
  return (
    <div className="space-y-5">
      {researchDomains.length > 0 && (
        <Card className="p-5">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2.5">
            Research Domains
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {researchDomains.map((dom, i) => (
              <StatusPill key={i} variant="navy">
                {dom}
              </StatusPill>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-navy-900" strokeWidth={1.5} />
          Publications (
          <span className="font-mono tabular-nums">{publications.length}</span>)
        </h3>
        {publications.length === 0 ? (
          <p className="text-xs text-slate-500">
            No publications extracted from this resume.
          </p>
        ) : (
          <div className="divide-y divide-slate-200/60">
            {publications.map((pub, i) => (
              <div key={i} className="py-2.5 first:pt-0 last:pb-0 space-y-1">
                <div className="text-xs font-semibold text-slate-900">
                  {pub.title}
                </div>
                <div className="text-[11px] text-slate-500 flex flex-wrap items-center gap-2">
                  <span>{pub.venue || "Venue unspecified"}</span>
                  {pub.year && (
                    <span className="font-mono tabular-nums text-slate-600">
                      ({pub.year})
                    </span>
                  )}
                  {pub.indexed && (
                    <span className="px-1.5 py-0.25 rounded bg-slate-100 border border-slate-200/80 text-slate-700 font-mono text-[10px]">
                      {pub.indexed}
                    </span>
                  )}
                  {pub.doi && (
                    <span className="font-mono text-navy-900 text-[10px]">
                      DOI: {pub.doi}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {researchProjects.length > 0 && (
        <Card className="p-5 space-y-2">
          <h3 className="text-sm font-bold text-slate-900">
            Funded Research Projects (
            <span className="font-mono tabular-nums">
              {researchProjects.length}
            </span>
            )
          </h3>
          <div className="divide-y divide-slate-200/60 text-xs">
            {researchProjects.map((rp, i) => (
              <div key={i} className="py-2">
                <div className="font-semibold text-slate-900">
                  {rp.title || "Untitled Project"}
                </div>
                <div className="text-slate-500 font-mono tabular-nums">
                  {[rp.role, rp.agency || rp.sponsor, rp.amount, rp.year]
                    .filter(Boolean)
                    .join(" • ")}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

interface EvidenceTabProps {
  candidate: Candidate;
}

export const EvidenceTab: React.FC<EvidenceTabProps> = ({ candidate }) => {
  return (
    <div className="space-y-5">
      {candidate.metadata && (
        <Card className="p-5">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
            <ShieldCheck
              className="w-4 h-4 text-emerald-600"
              strokeWidth={1.5}
            />
            Pipeline Execution &amp; Grounding Metadata
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">Model Used</div>
              <div className="font-mono font-semibold text-slate-800 mt-0.5 truncate">
                {candidate.metadata.model_name || "N/A"}
              </div>
            </div>
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">Extraction Method</div>
              <div className="font-mono font-semibold text-slate-800 mt-0.5">
                {candidate.metadata.extraction_method || "groq_text"}
              </div>
            </div>
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">Processing Latency</div>
              <div className="font-mono tabular-nums font-semibold text-slate-800 mt-0.5">
                {candidate.metadata.processing_time_seconds?.toFixed(2) ??
                  candidate.processing_time_seconds?.toFixed(2) ??
                  "0.00"}
                s
              </div>
            </div>
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">JSON Repaired</div>
              <div className="font-mono font-semibold text-slate-800 mt-0.5">
                {candidate.metadata.json_repaired ? "Yes (Flagged)" : "Clean"}
              </div>
            </div>
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        <CardHeader>
          <h3 className="text-sm font-bold text-slate-900">
            Traceable Source Evidence (
            <span className="font-mono tabular-nums">
              {candidate.source_evidence?.length ?? 0}
            </span>
            )
          </h3>
        </CardHeader>
        {(candidate.source_evidence?.length ?? 0) === 0 ? (
          <p className="p-5 text-xs text-slate-500">
            No field-level source evidence quotes recorded for this record.
          </p>
        ) : (
          <div className="divide-y divide-slate-200/60 text-xs">
            {candidate.source_evidence?.map((ev, i) => (
              <div key={i} className="p-4 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-semibold text-navy-900">
                    {ev.field}
                  </span>
                  <div className="flex items-center gap-1.5 font-mono tabular-nums text-[11px] text-slate-600">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200/80">
                      p. {ev.source_page ?? 1}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-slate-50 border border-slate-200/80">
                      {Math.round(ev.confidence * 100)}%
                    </span>
                  </div>
                </div>
                <p className="text-slate-600 italic">
                  &ldquo;{ev.evidence}&rdquo;
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

interface SourceTabProps {
  candidate: Candidate;
  fileUrl: string;
  isPdf: boolean;
  markdownResult: ResumeResultResponse | null;
}

export const SourceTab: React.FC<SourceTabProps> = ({
  candidate,
  fileUrl,
  isPdf,
  markdownResult,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <Card className="overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-slate-200/80 flex items-center justify-between gap-2">
          <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5 truncate">
            <FileText
              className="w-4 h-4 text-navy-900 shrink-0"
              strokeWidth={1.5}
            />
            {candidate.file_name}
          </span>
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-navy-900 hover:underline shrink-0"
          >
            Open Tab
          </a>
        </div>
        {isPdf ? (
          <iframe
            src={fileUrl}
            title={`Source PDF for ${candidate.name}`}
            className="w-full h-[640px] bg-slate-100"
          />
        ) : (
          <div className="p-4 flex items-center justify-center bg-slate-50 min-h-[420px]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={fileUrl}
              alt={candidate.file_name}
              className="max-h-[600px] w-auto rounded-md border border-slate-200/80"
            />
          </div>
        )}
      </Card>

      <Card className="overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-slate-200/80">
          <span className="text-xs font-bold text-slate-800">
            Generated Profile Markdown (<span className="font-mono">resume.md</span>)
          </span>
        </div>
        <pre className="p-4 text-xs font-mono text-slate-700 whitespace-pre-wrap overflow-y-auto h-[640px] bg-slate-50/40">
          {markdownResult?.markdown ||
            "No cached resume.md snapshot found for this candidate."}
        </pre>
      </Card>
    </div>
  );
};
