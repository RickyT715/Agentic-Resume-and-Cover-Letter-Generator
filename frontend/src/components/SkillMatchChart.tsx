import { useState } from "react"
import { Badge } from "./ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card"
import { BarChart2, CheckCircle, XCircle, Target, ChevronDown, ChevronRight } from "lucide-react"

interface EvaluationData {
  ats_score: number
  ats_breakdown: {
    keyword_similarity: number
    semantic_similarity: number
    skill_coverage: number
    fuzzy_match: number
    resume_quality: number
    section_bonus: number
    action_verbs_score: number
    quantified_score: number
    section_score: number
    format_score: number
  }
  matched_keywords: string[]
  missing_keywords: string[]
  combined_score: number
  passed: boolean
  llm_score?: number | null
  llm_breakdown?: {
    keyword_alignment: number
    professional_tone: number
    quantified_achievements: number
    relevance: number
    ats_compliance: number
    reasoning: string
    improvements: string[]
  } | null
}

interface SkillMatchChartProps {
  evaluation: EvaluationData
}

function ScoreBar({ label, value, color = "blue" }: { label: string; value: number; color?: string }) {
  const percentage = Math.round(value * 100)
  const colorClasses: Record<string, string> = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
    red: "bg-red-500",
    purple: "bg-purple-500",
  }
  const bgClass = percentage >= 70 ? colorClasses.green : percentage >= 50 ? colorClasses.yellow : colorClasses.red

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 dark:text-gray-400 w-40 flex-shrink-0">{label}</span>
      <div className="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${bgClass} transition-all duration-500`} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-12 text-right">{percentage}%</span>
    </div>
  )
}

function SmallScoreBar({ label, value }: { label: string; value: number }) {
  const percentage = Math.round(value * 100)
  const bgClass = percentage >= 70 ? "bg-green-400" : percentage >= 50 ? "bg-yellow-400" : "bg-red-400"

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 dark:text-gray-500 w-32 flex-shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${bgClass} transition-all duration-500`} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400 w-10 text-right">{percentage}%</span>
    </div>
  )
}

export function SkillMatchChart({ evaluation }: SkillMatchChartProps) {
  const { ats_breakdown, matched_keywords, missing_keywords, combined_score, passed } = evaluation
  const [qualityExpanded, setQualityExpanded] = useState(false)

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2">
        <BarChart2 className="w-4 h-4 text-blue-500" />
        <CardTitle>Resume Evaluation</CardTitle>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant={passed ? "success" : "warning"}>
            {passed ? "Passed" : "Needs Improvement"}
          </Badge>
          <span className="text-lg font-bold text-gray-800 dark:text-gray-200">
            {Math.round(combined_score * 100)}%
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* ATS Score Breakdown */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5" />
            ATS Score Breakdown
          </h4>
          <ScoreBar label="Keyword Relevance" value={ats_breakdown.keyword_similarity} />
          <ScoreBar label="Semantic Match" value={ats_breakdown.semantic_similarity} />
          <ScoreBar label="Skill Coverage" value={ats_breakdown.skill_coverage} />
          <ScoreBar label="Fuzzy Match" value={ats_breakdown.fuzzy_match} />
          <ScoreBar label="Resume Quality" value={ats_breakdown.resume_quality} />
          <ScoreBar label="Section Placement" value={ats_breakdown.section_bonus} />

          {/* Collapsible Quality Details */}
          <div className="ml-2">
            <button
              onClick={() => setQualityExpanded(!qualityExpanded)}
              className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              {qualityExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              Quality Details
            </button>
            {qualityExpanded && (
              <div className="mt-2 ml-4 space-y-1.5">
                <SmallScoreBar label="Action Verbs" value={ats_breakdown.action_verbs_score} />
                <SmallScoreBar label="Quantified Results" value={ats_breakdown.quantified_score} />
                <SmallScoreBar label="Sections" value={ats_breakdown.section_score} />
                <SmallScoreBar label="Format" value={ats_breakdown.format_score} />
              </div>
            )}
          </div>
        </div>

        {/* Keywords */}
        <div className="grid grid-cols-2 gap-4">
          {matched_keywords.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-green-700 dark:text-green-400 flex items-center gap-1.5 mb-2">
                <CheckCircle className="w-3.5 h-3.5" />
                Matched Skills ({matched_keywords.length})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {matched_keywords.slice(0, 12).map((kw) => (
                  <Badge key={kw} variant="success">{kw}</Badge>
                ))}
              </div>
            </div>
          )}
          {missing_keywords.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-red-700 dark:text-red-400 flex items-center gap-1.5 mb-2">
                <XCircle className="w-3.5 h-3.5" />
                Missing Skills ({missing_keywords.length})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {missing_keywords.slice(0, 8).map((kw) => (
                  <Badge key={kw} variant="error">{kw}</Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* LLM Judge Results */}
        {evaluation.llm_breakdown && (
          <div className="space-y-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Expert Review (LLM Score: {Math.round((evaluation.llm_score || 0) * 100)}%)
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 italic">
              {evaluation.llm_breakdown.reasoning}
            </p>
            {evaluation.llm_breakdown.improvements.length > 0 && (
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                {evaluation.llm_breakdown.improvements.map((imp, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-yellow-500 mt-0.5">-</span>
                    {imp}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
