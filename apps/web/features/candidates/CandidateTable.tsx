"use client";

import React, { useMemo, useState } from "react";
import {
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  GitCompare,
  Trash2,
  Eye,
  X,
  ExternalLink,
} from "lucide-react";
import { Candidate, JobDescription } from "../../types/candidate";
import {
  Button,
  Card,
  StatusPill,
  eligibilityPillVariant,
  tierPillVariant,
} from "../../components/ui";

interface CandidateTableProps {
  candidates: Candidate[];
  activeJd: JobDescription | null;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  onSelectCandidate: (candidate: Candidate) => void;
  selectedForCompare: string[];
  onToggleCompare: (id: string) => void;
  onOpenCompare: () => void;
  onDeleteCandidate: (id: string) => Promise<void>;
  onClearAll: () => Promise<void>;
}

type SortKey =
  | "name"
  | "overall_score"
  | "dynamic_score"
  | "teaching_years"
  | "publications_count"
  | "confidence";

function escapeCsvCell(val: string | number | null | undefined): string {
  const s = val === null || val === undefined ? "" : String(val);
  if (s.includes(",") || s.includes('"') || s.includes("\n")) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

export const CandidateTable: React.FC<CandidateTableProps> = ({
  candidates,
  activeJd,
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onSelectCandidate,
  selectedForCompare,
  onToggleCompare,
  onOpenCompare,
  onDeleteCandidate,
  onClearAll,
}) => {
  const [degreeFilter, setDegreeFilter] = useState("all");
  const [instFilter, setInstFilter] = useState("all");
  const [tierFilter, setTierFilter] = useState("all");
  const [linksOnly, setLinksOnly] = useState(false);
  const [minTeaching, setMinTeaching] = useState("0");
  const [sortBy, setSortBy] = useState<SortKey>(
    activeJd ? "dynamic_score" : "overall_score"
  );
  const [sortDesc, setSortDesc] = useState(true);
  const [confirmClear, setConfirmClear] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const uniqueDegrees = useMemo(
    () =>
      Array.from(
        new Set(candidates.map((c) => c.highest_degree).filter(Boolean))
      ).sort(),
    [candidates]
  );

  const uniqueInstitutions = useMemo(
    () =>
      Array.from(
        new Set(
          candidates
            .map((c) => c.highest_institution_category)
            .filter(Boolean)
        )
      ).sort(),
    [candidates]
  );

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const minT = Number(minTeaching) || 0;

    return candidates
      .filter((c) => {
        if (statusFilter !== "all" && c.eligibility_status !== statusFilter) {
          return false;
        }
        if (degreeFilter !== "all" && c.highest_degree !== degreeFilter) {
          return false;
        }
        if (
          instFilter !== "all" &&
          c.highest_institution_category !== instFilter
        ) {
          return false;
        }
        if (
          activeJd &&
          tierFilter !== "all" &&
          c.jd_evaluation?.recommendation_tier !== tierFilter
        ) {
          return false;
        }
        if (
          linksOnly &&
          (c.academic_links?.length ?? 0) === 0 &&
          !c.has_google_scholar &&
          !c.has_orcid
        ) {
          return false;
        }
        if ((c.teaching_years ?? 0) < minT) {
          return false;
        }
        if (!q) return true;
        const haystack = [
          c.name,
          c.email,
          c.highest_degree,
          c.highest_institution,
          c.highest_institution_category,
          c.file_name,
          c.current_designation,
          ...(c.skills ?? []),
          ...(c.courses_taught?.map((crs) => crs.course_name) ?? []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(q);
      })
      .sort((a, b) => {
        const dir = sortDesc ? -1 : 1;
        if (sortBy === "name") {
          return a.name.localeCompare(b.name) * dir;
        }
        if (sortBy === "dynamic_score") {
          return (
            ((a.jd_evaluation?.dynamic_score ?? -1) -
              (b.jd_evaluation?.dynamic_score ?? -1)) *
            dir
          );
        }
        return ((a[sortBy] ?? 0) - (b[sortBy] ?? 0)) * dir;
      });
  }, [
    candidates,
    activeJd,
    searchQuery,
    statusFilter,
    degreeFilter,
    instFilter,
    tierFilter,
    linksOnly,
    minTeaching,
    sortBy,
    sortDesc,
  ]);

  const toggleSort = (col: SortKey) => {
    if (sortBy === col) {
      setSortDesc((d) => !d);
    } else {
      setSortBy(col);
      setSortDesc(true);
    }
  };

  const renderSortIcon = (col: SortKey) => {
    if (sortBy !== col) {
      return (
        <ArrowUpDown className="w-3 h-3 text-slate-400" strokeWidth={1.5} />
      );
    }
    return sortDesc ? (
      <ArrowDown className="w-3 h-3 text-navy-900" strokeWidth={1.5} />
    ) : (
      <ArrowUp className="w-3 h-3 text-navy-900" strokeWidth={1.5} />
    );
  };

  const hasActiveFilters =
    statusFilter !== "all" ||
    degreeFilter !== "all" ||
    instFilter !== "all" ||
    (activeJd && tierFilter !== "all") ||
    linksOnly ||
    minTeaching !== "0" ||
    searchQuery.trim() !== "";

  const resetFilters = () => {
    onStatusFilterChange("all");
    setDegreeFilter("all");
    setInstFilter("all");
    setTierFilter("all");
    setLinksOnly(false);
    setMinTeaching("0");
    onSearchChange("");
  };

  const handleExportCsv = () => {
    const headers = [
      "ID",
      "Name",
      "Email",
      "Eligibility",
      "Review Status",
      "Rule Score %",
      "Confidence",
      "Grounding",
      "Highest Degree",
      "Institution",
      "Institution Category",
      "Teaching Years",
      "Total Years",
      "Publications",
      "Source File",
    ];
    const rows = filtered.map((c) =>
      [
        c.id,
        c.name,
        c.email,
        c.eligibility_status,
        c.review_status,
        c.overall_score,
        c.confidence,
        c.grounding_score,
        c.highest_degree,
        c.highest_institution,
        c.highest_institution_category,
        c.teaching_years,
        c.total_years,
        c.publications_count,
        c.file_name,
      ]
        .map(escapeCsvCell)
        .join(",")
    );
    const csvContent = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `facultyscreen_candidates_${filtered.length}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <Card className="p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[240px]">
          {/* Inline search only on < md where Navbar hides global search */}
          <div className="relative w-full sm:w-56 md:hidden">
            <Search
              className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
              strokeWidth={1.5}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Filter name, institution, skill..."
              className="w-full pl-8 pr-7 py-1.5 text-xs bg-slate-50 border border-slate-200/80 rounded-md focus:outline-none focus:bg-white focus:border-navy-900"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => onSearchChange("")}
                aria-label="Clear filter"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" strokeWidth={1.5} />
              </button>
            )}
          </div>

          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
            aria-label="Filter by eligibility status"
            className="text-xs px-2.5 py-1.5 rounded-md border border-slate-200/80 bg-white text-slate-700 focus:outline-none focus:border-navy-900"
          >
            <option value="all">All Statuses</option>
            <option value="eligible">Eligible</option>
            <option value="needs_review">Needs Review</option>
            <option value="disqualified">Disqualified</option>
          </select>

          <select
            value={degreeFilter}
            onChange={(e) => setDegreeFilter(e.target.value)}
            aria-label="Filter by degree"
            className="text-xs px-2.5 py-1.5 rounded-md border border-slate-200/80 bg-white text-slate-700 focus:outline-none focus:border-navy-900"
          >
            <option value="all">All Degrees</option>
            {uniqueDegrees.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>

          <select
            value={instFilter}
            onChange={(e) => setInstFilter(e.target.value)}
            aria-label="Filter by institution category"
            className="text-xs px-2.5 py-1.5 rounded-md border border-slate-200/80 bg-white text-slate-700 focus:outline-none focus:border-navy-900"
          >
            <option value="all">All Institution Tiers</option>
            {uniqueInstitutions.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          <select
            value={minTeaching}
            onChange={(e) => setMinTeaching(e.target.value)}
            aria-label="Filter by minimum teaching years"
            className="text-xs px-2.5 py-1.5 rounded-md border border-slate-200/80 bg-white text-slate-700 focus:outline-none focus:border-navy-900"
          >
            <option value="0">Teaching: Any</option>
            <option value="3">Teaching &ge; 3 yrs</option>
            <option value="5">Teaching &ge; 5 yrs</option>
            <option value="10">Teaching &ge; 10 yrs</option>
          </select>

          {activeJd && (
            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              aria-label="Filter by JD recommendation tier"
              className="text-xs px-2.5 py-1.5 rounded-md border border-navy-200 bg-navy-50/40 text-navy-900 font-medium focus:outline-none focus:border-navy-900"
            >
              <option value="all">All JD Match Tiers</option>
              <option value="strong_match">Strong Match</option>
              <option value="strong_alternative_fit">
                Strong Alternative Fit
              </option>
              <option value="conditional_review">Conditional Review</option>
              <option value="low_alignment">Low Alignment</option>
            </select>
          )}

          <label
            className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border cursor-pointer transition ${
              linksOnly
                ? "border-navy-200 bg-navy-50/50 text-navy-900 font-medium"
                : "border-slate-200/80 bg-slate-50/70 text-slate-700"
            }`}
          >
            <input
              type="checkbox"
              checked={linksOnly}
              onChange={(e) => setLinksOnly(e.target.checked)}
              className="rounded border-slate-300 accent-navy-900"
            />
            Scholar / ORCID Links
          </label>

          {searchQuery.trim() && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="hidden md:inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md bg-navy-50 text-navy-900 border border-navy-200/80 hover:bg-navy-100/70 cursor-pointer"
            >
              Search: &ldquo;{searchQuery.trim()}&rdquo;
              <X className="w-3 h-3" strokeWidth={1.5} />
            </button>
          )}

          {hasActiveFilters && (
            <Button variant="ghost" size="xs" onClick={resetFilters}>
              Reset
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {selectedForCompare.length >= 2 && (
            <Button variant="primary" size="sm" onClick={onOpenCompare}>
              <GitCompare className="w-3.5 h-3.5" strokeWidth={1.5} />
              Compare (
              <span className="font-mono tabular-nums">
                {selectedForCompare.length}
              </span>
              )
            </Button>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={handleExportCsv}
            disabled={filtered.length === 0}
          >
            <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
            Export CSV
          </Button>

          {candidates.length > 0 &&
            (confirmClear ? (
              <div className="inline-flex items-center gap-1.5">
                <Button
                  variant="dangerSolid"
                  size="xs"
                  onClick={async () => {
                    await onClearAll();
                    setConfirmClear(false);
                  }}
                >
                  Confirm Reset
                </Button>
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() => setConfirmClear(false)}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="danger"
                size="sm"
                onClick={() => setConfirmClear(true)}
              >
                <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                Clear Pool
              </Button>
            ))}
        </div>
      </Card>

      <div className="text-xs text-slate-500 px-1 flex items-center justify-between">
        <span>
          Showing{" "}
          <strong className="font-mono tabular-nums text-slate-900">
            {filtered.length}
          </strong>{" "}
          of{" "}
          <span className="font-mono tabular-nums">{candidates.length}</span>{" "}
          candidates
        </span>
        {selectedForCompare.length > 0 && (
          <span className="text-navy-900 font-medium font-mono tabular-nums">
            {selectedForCompare.length}/4 selected for side-by-side comparison
          </span>
        )}
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="sticky top-0 z-10 border-b border-slate-200/80 bg-slate-50/95 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                <th className="py-2.5 px-4 w-10">Cmp</th>
                <th className="py-2.5 px-4">
                  <button
                    type="button"
                    onClick={() => toggleSort("name")}
                    className={`inline-flex items-center gap-1 cursor-pointer ${
                      sortBy === "name"
                        ? "text-navy-900"
                        : "hover:text-slate-900"
                    }`}
                  >
                    Candidate {renderSortIcon("name")}
                  </button>
                </th>
                <th className="py-2.5 px-4">Degree &amp; Institution</th>
                <th className="py-2.5 px-4 text-right">
                  <button
                    type="button"
                    onClick={() => toggleSort("teaching_years")}
                    className={`inline-flex items-center gap-1 cursor-pointer ${
                      sortBy === "teaching_years"
                        ? "text-navy-900"
                        : "hover:text-slate-900"
                    }`}
                  >
                    Teaching {renderSortIcon("teaching_years")}
                  </button>
                </th>
                <th className="py-2.5 px-4 text-right">
                  <button
                    type="button"
                    onClick={() => toggleSort("publications_count")}
                    className={`inline-flex items-center gap-1 cursor-pointer ${
                      sortBy === "publications_count"
                        ? "text-navy-900"
                        : "hover:text-slate-900"
                    }`}
                  >
                    Pubs {renderSortIcon("publications_count")}
                  </button>
                </th>
                <th className="py-2.5 px-4 text-right">
                  <button
                    type="button"
                    onClick={() =>
                      toggleSort(activeJd ? "dynamic_score" : "overall_score")
                    }
                    className={`inline-flex items-center gap-1 cursor-pointer ${
                      sortBy === "dynamic_score" || sortBy === "overall_score"
                        ? "text-navy-900"
                        : "hover:text-slate-900"
                    }`}
                  >
                    {activeJd ? "JD Fit" : "Score"}{" "}
                    {renderSortIcon(
                      activeJd ? "dynamic_score" : "overall_score"
                    )}
                  </button>
                </th>
                <th className="py-2.5 px-4 text-right">
                  <button
                    type="button"
                    onClick={() => toggleSort("confidence")}
                    className={`inline-flex items-center gap-1 cursor-pointer ${
                      sortBy === "confidence"
                        ? "text-navy-900"
                        : "hover:text-slate-900"
                    }`}
                  >
                    Conf {renderSortIcon("confidence")}
                  </button>
                </th>
                <th className="py-2.5 px-4">
                  {activeJd ? "Recommendation & Approval" : "Status"}
                </th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/60 text-xs">
              {filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                    className="py-10 text-center text-slate-500 text-sm"
                  >
                    No candidates match the active filters.
                  </td>
                </tr>
              ) : (
                filtered.map((cand) => {
                  const isCompared = selectedForCompare.includes(cand.id);
                  return (
                    <tr
                      key={cand.id}
                      onClick={() => onSelectCandidate(cand)}
                      className="even:bg-slate-50/40 hover:bg-slate-100/50 cursor-pointer transition"
                    >
                      <td
                        className="py-2.5 px-4"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={isCompared}
                          onChange={() => onToggleCompare(cand.id)}
                          aria-label={`Select ${cand.name} for comparison`}
                          className="rounded border-slate-300 accent-navy-900 cursor-pointer"
                        />
                      </td>
                      <td className="py-2.5 px-4">
                        <div className="font-semibold text-slate-900">
                          {cand.name}
                        </div>
                        <div className="text-[11px] text-slate-500 truncate max-w-[210px]">
                          {cand.current_designation || cand.file_name}
                        </div>
                        {(cand.academic_links?.length ?? 0) > 0 && (
                          <div
                            className="flex flex-wrap gap-1 mt-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {cand.academic_links?.slice(0, 3).map((lnk) => (
                              <a
                                key={`${lnk.platform}-${lnk.url}`}
                                href={lnk.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-0.5 px-1.5 py-0.25 text-[10px] font-medium rounded border border-slate-200/80 bg-white text-navy-900 hover:bg-navy-50 transition"
                              >
                                {lnk.platform.replace("_", " ")}
                                <ExternalLink
                                  className="w-2.5 h-2.5"
                                  strokeWidth={1.5}
                                />
                              </a>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="py-2.5 px-4">
                        <div className="font-medium text-slate-800">
                          {cand.highest_degree}
                        </div>
                        <div className="text-[11px] text-slate-500 truncate max-w-[220px]">
                          {cand.highest_institution} (
                          {cand.highest_institution_category})
                        </div>
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                        <div>{cand.teaching_years} yrs</div>
                        {(cand.courses_taught_count ?? 0) > 0 && (
                          <div className="text-[10px] text-slate-500">
                            {cand.courses_taught_count} courses
                          </div>
                        )}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                        {cand.publications_count}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono font-semibold text-slate-900 tabular-nums">
                        {activeJd
                          ? cand.jd_evaluation
                            ? `${cand.jd_evaluation.dynamic_score.toFixed(1)}%`
                            : "Pending"
                          : `${cand.overall_score.toFixed(1)}%`}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-600">
                        {Math.round(cand.confidence * 100)}%
                      </td>
                      <td className="py-2.5 px-4">
                        {activeJd && cand.jd_evaluation ? (
                          <div className="space-y-1">
                            <StatusPill
                              variant={tierPillVariant(
                                cand.jd_evaluation.recommendation_tier
                              )}
                              className="capitalize"
                            >
                              {cand.jd_evaluation.recommendation_tier.replace(
                                /_/g,
                                " "
                              )}
                            </StatusPill>
                            {cand.jd_evaluation.approval_status !==
                              "pending" && (
                              <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                                Decision:{" "}
                                {cand.jd_evaluation.approval_status.replace(
                                  /_/g,
                                  " "
                                )}
                              </div>
                            )}
                          </div>
                        ) : (
                          <StatusPill
                            variant={eligibilityPillVariant(
                              cand.eligibility_status
                            )}
                            className="capitalize"
                          >
                            {cand.eligibility_status.replace("_", " ")}
                          </StatusPill>
                        )}
                      </td>
                      <td
                        className="py-2.5 px-4 text-right"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => onSelectCandidate(cand)}
                            title="Inspect candidate"
                            aria-label={`Inspect ${cand.name}`}
                            className="p-1.5 rounded-md text-slate-500 hover:text-navy-900 hover:bg-navy-50 cursor-pointer"
                          >
                            <Eye className="w-3.5 h-3.5" strokeWidth={1.5} />
                          </button>

                          {confirmDeleteId === cand.id ? (
                            <div className="inline-flex items-center gap-1">
                              <Button
                                variant="dangerSolid"
                                size="xs"
                                onClick={async () => {
                                  await onDeleteCandidate(cand.id);
                                  setConfirmDeleteId(null);
                                }}
                              >
                                Delete
                              </Button>
                              <Button
                                variant="ghost"
                                size="xs"
                                onClick={() => setConfirmDeleteId(null)}
                              >
                                No
                              </Button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setConfirmDeleteId(cand.id)}
                              title="Remove candidate"
                              aria-label={`Remove ${cand.name}`}
                              className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 cursor-pointer"
                            >
                              <Trash2
                                className="w-3.5 h-3.5"
                                strokeWidth={1.5}
                              />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
