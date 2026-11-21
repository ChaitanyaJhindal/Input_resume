'use client';

import React, { useState, useMemo } from 'react';
import { 
  Search, Filter, ChevronUp, ChevronDown, CheckCircle2, 
  AlertTriangle, XCircle, Eye, GitCompare, Download, SlidersHorizontal, Trash2
} from 'lucide-react';
import { Candidate } from '../../types/candidate';

interface CandidateTableProps {
  candidates: Candidate[];
  onSelectCandidate: (candidateId: string) => void;
  onCompareCandidates: (candidateIds: string[]) => void;
  onOpenUploadModal?: () => void;
  onDeleteCandidate?: (candidateId: string) => void;
  onClearAll?: () => void;
}

export const CandidateTable: React.FC<CandidateTableProps> = ({
  candidates,
  onSelectCandidate,
  onCompareCandidates,
  onOpenUploadModal,
  onDeleteCandidate,
  onClearAll
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [degreeFilter, setDegreeFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [minTeachingFilter, setMinTeachingFilter] = useState<number>(0);
  const [uploadedOnlyFilter, setUploadedOnlyFilter] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [sortField, setSortField] = useState<keyof Candidate>('overall_score');
  const [sortAsc, setSortAsc] = useState(false);
  const [density, setDensity] = useState<'comfortable' | 'compact'>('comfortable');

  // Filter logic
  const filteredCandidates = useMemo(() => {
    return candidates.filter((cand) => {
      // Uploaded Only
      if (uploadedOnlyFilter && !cand.is_uploaded) return false;

      // Search
      const q = searchTerm.toLowerCase();
      const matchesSearch = !q || (
        cand.name.toLowerCase().includes(q) ||
        (cand.highest_institution && cand.highest_institution.toLowerCase().includes(q)) ||
        (cand.highest_degree && cand.highest_degree.toLowerCase().includes(q)) ||
        (cand.email && cand.email.toLowerCase().includes(q))
      );

      // Degree
      const matchesDegree = degreeFilter === 'ALL' || cand.highest_degree === degreeFilter;

      // Category
      const matchesCategory = categoryFilter === 'ALL' || cand.highest_institution_category === categoryFilter;

      // Status
      const matchesStatus = statusFilter === 'ALL' || cand.eligibility_status === statusFilter;

      // Teaching Exp
      const matchesExp = cand.teaching_years >= minTeachingFilter;

      return matchesSearch && matchesDegree && matchesCategory && matchesStatus && matchesExp;
    });
  }, [candidates, searchTerm, degreeFilter, categoryFilter, statusFilter, minTeachingFilter]);

  // Sort logic
  const sortedCandidates = useMemo(() => {
    return [...filteredCandidates].sort((a, b) => {
      const aVal = a[sortField] ?? '';
      const bVal = b[sortField] ?? '';
      if (aVal < bVal) return sortAsc ? -1 : 1;
      if (aVal > bVal) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [filteredCandidates, sortField, sortAsc]);

  const handleSort = (field: keyof Candidate) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(sortedCandidates.slice(0, 4).map(c => c.id));
    } else {
      setSelectedIds([]);
    }
  };

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      if (selectedIds.length >= 4) {
        alert("You can select up to 4 candidates for comparison.");
        return;
      }
      setSelectedIds([...selectedIds, id]);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header and Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">Candidate Resume Library</h1>
            <p className="text-xs text-slate-500">
              Showing {sortedCandidates.length} of {candidates.length} candidates extracted from source documents.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* View Switcher: All vs Uploaded Only */}
            <div className="flex items-center border border-slate-200 rounded-md overflow-hidden bg-slate-50 text-xs">
              <button
                onClick={() => setUploadedOnlyFilter(false)}
                className={`px-3 py-1 text-xs font-semibold cursor-pointer transition-colors ${!uploadedOnlyFilter ? 'bg-blue-900 text-white shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                All Resumes ({candidates.length})
              </button>
              <button
                onClick={() => setUploadedOnlyFilter(true)}
                className={`px-3 py-1 text-xs font-semibold cursor-pointer transition-colors ${uploadedOnlyFilter ? 'bg-blue-900 text-white shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Uploaded Only ({candidates.filter(c => c.is_uploaded).length})
              </button>
            </div>

            {onOpenUploadModal && (
              <button
                onClick={onOpenUploadModal}
                className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer transition-colors"
              >
                <span>+ Upload Resumes</span>
              </button>
            )}

            {onClearAll && (
              <button
                onClick={onClearAll}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-md text-xs font-semibold shadow-2xs cursor-pointer transition-colors"
                title="Clear all stored candidate profiles and screening data"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear All</span>
              </button>
            )}

            {selectedIds.length >= 2 && (
              <button
                onClick={() => onCompareCandidates(selectedIds)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer animate-pulse"
              >
                <GitCompare className="w-3.5 h-3.5" />
                <span>Compare ({selectedIds.length})</span>
              </button>
            )}

            <div className="flex items-center border border-slate-200 rounded-md overflow-hidden bg-slate-50 text-xs">
              <button
                onClick={() => setDensity('comfortable')}
                className={`px-2 py-1 text-xs font-medium cursor-pointer ${density === 'comfortable' ? 'bg-white text-slate-900 font-semibold shadow-2xs' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Comfortable
              </button>
              <button
                onClick={() => setDensity('compact')}
                className={`px-2 py-1 text-xs font-medium cursor-pointer ${density === 'compact' ? 'bg-white text-slate-900 font-semibold shadow-2xs' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Compact
              </button>
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2.5 pt-2 border-t border-slate-100 text-xs">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search keyword..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-700"
            />
          </div>

          <div>
            <select
              value={degreeFilter}
              onChange={(e) => setDegreeFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
            >
              <option value="ALL">Degree: All Levels</option>
              <option value="PhD / Doctorate">PhD / Doctorate</option>
              <option value="Postdoctoral">Postdoctoral</option>
              <option value="Postgraduate / Masters">Postgraduate / Masters</option>
              <option value="Undergraduate">Undergraduate</option>
            </select>
          </div>

          <div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
            >
              <option value="ALL">Institution: All Types</option>
              <option value="IIT">IIT</option>
              <option value="NIT">NIT</option>
              <option value="IIIT">IIIT</option>
              <option value="Central University">Central University</option>
              <option value="State University">State University</option>
              <option value="Deemed University">Deemed University</option>
              <option value="Private University">Private University</option>
              <option value="International University">International</option>
            </select>
          </div>

          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
            >
              <option value="ALL">Status: All Statuses</option>
              <option value="eligible">Eligible (Passed)</option>
              <option value="needs_review">Needs Review</option>
              <option value="disqualified">Disqualified</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1">
            <span className="text-slate-500 whitespace-nowrap text-[11px]">Min Teach:</span>
            <input
              type="number"
              min="0"
              max="30"
              step="1"
              value={minTeachingFilter}
              onChange={(e) => setMinTeachingFilter(Number(e.target.value))}
              className="w-12 px-1 py-0.5 border border-slate-200 rounded text-center text-xs font-mono font-semibold"
            />
            <span className="text-slate-400 text-[11px]">yrs</span>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-100 text-slate-600 border-b border-slate-200 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-2.5 px-3 text-center w-8">
                  <input
                    type="checkbox"
                    checked={selectedIds.length > 0 && selectedIds.length === Math.min(4, sortedCandidates.length)}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="rounded text-blue-900 cursor-pointer"
                  />
                </th>
                <th className="py-2.5 px-4 cursor-pointer hover:bg-slate-200/60" onClick={() => handleSort('name')}>
                  <div className="flex items-center gap-1">
                    <span>Candidate</span>
                    {sortField === 'name' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>
                <th className="py-2.5 px-4 cursor-pointer hover:bg-slate-200/60" onClick={() => handleSort('highest_degree')}>
                  <div className="flex items-center gap-1">
                    <span>Degree</span>
                    {sortField === 'highest_degree' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>
                <th className="py-2.5 px-4 cursor-pointer hover:bg-slate-200/60" onClick={() => handleSort('highest_institution')}>
                  <div className="flex items-center gap-1">
                    <span>Institution</span>
                    {sortField === 'highest_institution' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>
                <th className="py-2.5 px-3 text-center">Category</th>
                <th className="py-2.5 px-3 text-center cursor-pointer hover:bg-slate-200/60" onClick={() => handleSort('teaching_years')}>
                  <div className="flex items-center justify-center gap-1">
                    <span>Teaching</span>
                    {sortField === 'teaching_years' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>
                <th className="py-2.5 px-3 text-center cursor-pointer hover:bg-slate-200/60" onClick={() => handleSort('research_years')}>
                  <div className="flex items-center justify-center gap-1">
                    <span>Research</span>
                    {sortField === 'research_years' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>
                <th className="py-2.5 px-3 text-center cursor-pointer hover:bg-slate-200/60" onClick={() => handleSort('publications_count')}>
                  <div className="flex items-center justify-center gap-1">
                    <span>Pubs</span>
                    {sortField === 'publications_count' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>
                <th className="py-2.5 px-3 text-center cursor-pointer hover:bg-slate-200/60" onClick={() => handleSort('overall_score')}>
                  <div className="flex items-center justify-center gap-1">
                    <span>Score</span>
                    {sortField === 'overall_score' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>
                <th className="py-2.5 px-4 text-center">Screening Status</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedCandidates.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-slate-400">
                    No candidates found matching the selected filter criteria.
                  </td>
                </tr>
              ) : (
                sortedCandidates.map((cand) => {
                  const isSelected = selectedIds.includes(cand.id);
                  const py = density === 'comfortable' ? 'py-3' : 'py-1.5';

                  return (
                    <tr 
                      key={cand.id} 
                      className={`hover:bg-slate-50/80 transition-colors ${isSelected ? 'bg-blue-50/40' : ''}`}
                    >
                      <td className={`${py} px-3 text-center`}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(cand.id)}
                          className="rounded text-blue-900 cursor-pointer"
                        />
                      </td>
                      <td className={`${py} px-4 font-medium text-slate-900`}>
                        <div className="font-semibold text-slate-900 hover:text-blue-900 cursor-pointer" onClick={() => onSelectCandidate(cand.id)}>
                          {cand.name}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono truncate max-w-[200px]">
                          {cand.file_name}
                        </div>
                      </td>
                      <td className={`${py} px-4 font-medium text-slate-700`}>
                        <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${cand.highest_degree?.includes('PhD') || cand.highest_degree?.includes('Doctorate') ? 'bg-blue-50 text-blue-800 border border-blue-200' : 'bg-slate-100 text-slate-700'}`}>
                          {cand.highest_degree || 'Unspecified'}
                        </span>
                      </td>
                      <td className={`${py} px-4 text-slate-600 truncate max-w-[180px]`}>
                        {cand.highest_institution || '-'}
                      </td>
                      <td className={`${py} px-3 text-center`}>
                        <span className="inline-block px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-medium border border-slate-200">
                          {cand.highest_institution_category || 'Other'}
                        </span>
                      </td>
                      <td className={`${py} px-3 text-center font-mono font-medium text-slate-800`}>
                        {cand.teaching_years}y
                      </td>
                      <td className={`${py} px-3 text-center font-mono font-medium text-slate-800`}>
                        {cand.research_years}y
                      </td>
                      <td className={`${py} px-3 text-center font-mono font-medium text-slate-800`}>
                        {cand.publications_count}
                      </td>
                      <td className={`${py} px-3 text-center font-mono font-bold text-slate-900`}>
                        {cand.overall_score}%
                      </td>
                      <td className={`${py} px-4 text-center`}>
                        {cand.eligibility_status === 'eligible' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" /> Eligible
                          </span>
                        ) : cand.eligibility_status === 'needs_review' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                            <AlertTriangle className="w-3 h-3" /> Needs Review
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200">
                            <XCircle className="w-3 h-3" /> Disqualified
                          </span>
                        )}
                      </td>
                      <td className={`${py} px-4 text-right whitespace-nowrap`}>
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => onSelectCandidate(cand.id)}
                            className="px-2.5 py-1 text-xs font-semibold text-blue-900 hover:bg-blue-50 rounded border border-blue-200 transition-colors cursor-pointer inline-flex items-center gap-1"
                          >
                            <Eye className="w-3 h-3" />
                            <span>Inspect</span>
                          </button>
                          {onDeleteCandidate && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                if (confirm(`Delete candidate "${cand.name}" and remove their screening records?`)) {
                                  onDeleteCandidate(cand.id);
                                }
                              }}
                              className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded border border-transparent hover:border-rose-200 transition-colors cursor-pointer"
                              title="Delete candidate"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
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
      </div>
    </div>
  );
};
