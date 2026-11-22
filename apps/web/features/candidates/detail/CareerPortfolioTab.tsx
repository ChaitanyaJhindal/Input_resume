"use client";

import React from "react";
import { Award, BookOpen, Briefcase, GraduationCap } from "lucide-react";
import { Candidate } from "../../../types/candidate";
import { Card, StatusPill } from "../../../components/ui";

interface CareerPortfolioTabProps {
  candidate: Candidate;
}

export const CareerPortfolioTab: React.FC<CareerPortfolioTabProps> = ({
  candidate,
}) => {
  const coursesTaught = candidate.courses_taught ?? [];
  const supervision = candidate.supervision;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { label: "Total Tenure", val: candidate.total_years },
          { label: "Teaching", val: candidate.teaching_years },
          { label: "Research", val: candidate.research_years },
          { label: "Industry", val: candidate.industry_years },
          { label: "Admin", val: candidate.administrative_years ?? 0 },
        ].map((b) => (
          <Card key={b.label} className="p-3.5 text-center">
            <div className="text-[11px] text-slate-500">{b.label}</div>
            <div className="text-base font-bold font-mono tabular-nums text-slate-900 mt-0.5">
              {b.val} yrs
            </div>
          </Card>
        ))}
      </div>

      <Card className="p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <GraduationCap className="w-4 h-4 text-navy-900" strokeWidth={1.5} />
          Complete Academic Degrees &amp; Credentials (
          <span className="font-mono tabular-nums">
            {candidate.education.length}
          </span>
          )
        </h3>
        {candidate.education.length === 0 ? (
          <p className="text-xs text-slate-500">No degrees recorded.</p>
        ) : (
          <div className="divide-y divide-slate-200/60">
            {candidate.education.map((edu, idx) => (
              <div key={idx} className="py-3 first:pt-0 last:pb-0 space-y-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold text-slate-900">
                    {edu.degree}
                    {edu.field ? ` — ${edu.field}` : ""}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {edu.status === "in_progress" && (
                      <StatusPill variant="amber" className="text-[10px]">
                        In Progress
                      </StatusPill>
                    )}
                    <StatusPill variant="navy">
                      {edu.normalized_degree}
                    </StatusPill>
                  </div>
                </div>
                <div className="text-xs text-slate-600">
                  {edu.institution_normalized || edu.institution} &bull;{" "}
                  {edu.institution_category || "Other"} (
                  {edu.institution_tier || "Unclassified"})
                  {(edu.start_year || edu.graduation_year) && (
                    <span className="font-mono tabular-nums">
                      {" "}
                      &bull; {edu.start_year ? `${edu.start_year}–` : ""}
                      {edu.graduation_year ?? "Present"}
                    </span>
                  )}
                  {edu.gpa_or_honors ? ` • ${edu.gpa_or_honors}` : ""}
                </div>
                {edu.thesis_title && (
                  <div className="text-[11px] text-slate-500">
                    <strong>Thesis:</strong> {edu.thesis_title}
                    {edu.advisor ? ` (Advisor: ${edu.advisor})` : ""}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {(coursesTaught.length > 0 ||
        (candidate.teaching_interests?.length ?? 0) > 0 ||
        (supervision &&
          (supervision.phd_completed > 0 ||
            supervision.phd_ongoing > 0 ||
            supervision.masters_guided > 0 ||
            supervision.ug_projects_guided > 0))) && (
        <Card className="p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-navy-900" strokeWidth={1.5} />
            Courses Taught &amp; Teaching Portfolio (
            <span className="font-mono tabular-nums">
              {coursesTaught.length}
            </span>
            )
          </h3>

          {coursesTaught.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs">
              {coursesTaught.map((crs, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80 space-y-1"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-900">
                      {crs.course_code ? (
                        <span className="font-mono text-navy-900">
                          {crs.course_code}:{" "}
                        </span>
                      ) : null}
                      {crs.course_name}
                    </span>
                    <StatusPill variant="neutral" className="text-[10px] shrink-0">
                      {crs.level}
                    </StatusPill>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {[crs.role, crs.institution, crs.term_or_years]
                      .filter(Boolean)
                      .join(" • ")}
                  </div>
                </div>
              ))}
            </div>
          )}

          {(candidate.teaching_interests?.length ?? 0) > 0 && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Teaching Interests
              </div>
              <div className="flex flex-wrap gap-1.5">
                {candidate.teaching_interests?.map((ti, i) => (
                  <StatusPill key={i} variant="navy">
                    {ti}
                  </StatusPill>
                ))}
              </div>
            </div>
          )}

          {supervision &&
            (supervision.phd_completed > 0 ||
              supervision.phd_ongoing > 0 ||
              supervision.masters_guided > 0 ||
              supervision.ug_projects_guided > 0) && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs pt-3 border-t border-slate-200/60">
                <div className="p-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 text-center">
                  <div className="text-slate-500">PhD Completed</div>
                  <div className="font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                    {supervision.phd_completed}
                  </div>
                </div>
                <div className="p-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 text-center">
                  <div className="text-slate-500">PhD Ongoing</div>
                  <div className="font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                    {supervision.phd_ongoing}
                  </div>
                </div>
                <div className="p-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 text-center">
                  <div className="text-slate-500">Masters Guided</div>
                  <div className="font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                    {supervision.masters_guided}
                  </div>
                </div>
                <div className="p-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 text-center">
                  <div className="text-slate-500">UG Projects</div>
                  <div className="font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                    {supervision.ug_projects_guided}
                  </div>
                </div>
              </div>
            )}
        </Card>
      )}

      <Card className="p-5 space-y-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-navy-900" strokeWidth={1.5} />
          Employment History (
          <span className="font-mono tabular-nums">
            {candidate.employment.length}
          </span>
          )
        </h3>
        {candidate.employment.length === 0 ? (
          <p className="text-xs text-slate-500">
            No employment records extracted.
          </p>
        ) : (
          <div className="divide-y divide-slate-200/60">
            {candidate.employment.map((emp, idx) => (
              <div key={idx} className="py-3 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold text-slate-900">
                    {emp.title}
                  </span>
                  <span className="text-[11px] uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200/80 font-mono tabular-nums">
                    {emp.category} &bull; {emp.duration_years} yrs
                  </span>
                </div>
                <div className="text-xs text-slate-600 mt-0.5">
                  {emp.organization}{" "}
                  <span className="font-mono tabular-nums text-slate-500">
                    ({emp.start_date || "N/A"} –{" "}
                    {emp.is_current ? "Present" : emp.end_date || "N/A"})
                  </span>
                </div>
                {emp.description && (
                  <p className="text-xs text-slate-500 mt-1">
                    {emp.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {((candidate.skills?.length ?? 0) > 0 ||
        (candidate.awards?.length ?? 0) > 0 ||
        (candidate.certifications?.length ?? 0) > 0 ||
        (candidate.academic_service?.length ?? 0) > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {(candidate.skills?.length ?? 0) > 0 && (
            <Card className="p-5">
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-3">
                Technical &amp; Academic Skills
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {candidate.skills?.map((s, i) => (
                  <StatusPill key={i} variant="neutral">
                    {s}
                  </StatusPill>
                ))}
              </div>
            </Card>
          )}

          {((candidate.awards?.length ?? 0) > 0 ||
            (candidate.certifications?.length ?? 0) > 0 ||
            (candidate.academic_service?.length ?? 0) > 0) && (
            <Card className="p-5 space-y-3">
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Award className="w-3.5 h-3.5 text-navy-900" strokeWidth={1.5} />
                Awards, Service &amp; Certifications
              </h3>
              <ul className="list-disc pl-4 text-xs text-slate-700 space-y-1">
                {candidate.awards?.map((a, i) => (
                  <li key={`aw-${i}`}>{a}</li>
                ))}
                {candidate.academic_service?.map((svc, i) => (
                  <li key={`svc-${i}`}>{svc}</li>
                ))}
                {candidate.certifications?.map((c, i) => (
                  <li key={`cert-${i}`}>{c}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
