import { CheckCircle, Circle, Loader2, XCircle, Brain, Search, FileEdit, Shield, FileText, Printer, Send } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card"
import { Badge } from "./ui/badge"
import type { Task, StepProgress } from "../types/task"

interface AgentNode {
  id: string
  label: string
  icon: React.ReactNode
  description: string
  step: string // Maps to TaskStep
}

const V3_PIPELINE_NODES: AgentNode[] = [
  {
    id: "jd_analyzer",
    label: "JD Analysis",
    icon: <Search className="w-4 h-4" />,
    description: "Extracting skills, requirements, and role details",
    step: "generate_resume",
  },
  {
    id: "relevance_matcher",
    label: "Profile Match",
    icon: <Brain className="w-4 h-4" />,
    description: "Matching your profile to job requirements",
    step: "generate_resume",
  },
  {
    id: "resume_writer",
    label: "Resume Gen",
    icon: <FileEdit className="w-4 h-4" />,
    description: "Generating tailored LaTeX resume",
    step: "generate_resume",
  },
  {
    id: "quality_gate",
    label: "Quality Check",
    icon: <Shield className="w-4 h-4" />,
    description: "Evaluating resume quality and ATS score",
    step: "generate_resume",
  },
  {
    id: "compile_latex",
    label: "PDF Compile",
    icon: <Printer className="w-4 h-4" />,
    description: "Compiling LaTeX to PDF",
    step: "compile_latex",
  },
  {
    id: "cover_letter",
    label: "Cover Letter",
    icon: <Send className="w-4 h-4" />,
    description: "Generating personalized cover letter",
    step: "generate_cover_letter",
  },
]

function getNodeStatus(
  node: AgentNode,
  task: Task,
): "pending" | "running" | "completed" | "failed" | "skipped" {
  const stepProgress = task.steps.find((s) => s.step === node.step)
  if (!stepProgress) return "skipped"

  // For the v3 pipeline sub-nodes within the "generate_resume" step,
  // we infer status from step message content
  if (node.step === "generate_resume" && stepProgress.message) {
    const msg = stepProgress.message.toLowerCase()
    if (msg.includes(node.id.replace("_", " ")) || msg.includes(node.label.toLowerCase())) {
      return stepProgress.status as "running" | "completed" | "failed"
    }
  }

  return stepProgress.status as "pending" | "running" | "completed" | "failed"
}

interface AgentProgressProps {
  task: Task
}

export function AgentProgress({ task }: AgentProgressProps) {
  if (task.pipeline_version !== "v3") return null

  const nodes = task.generate_cover_letter
    ? V3_PIPELINE_NODES
    : V3_PIPELINE_NODES.filter((n) => n.id !== "cover_letter")

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2">
        <Brain className="w-4 h-4 text-purple-500" />
        <CardTitle>Multi-Agent Pipeline (v3)</CardTitle>
        <Badge variant="purple" className="ml-auto">LangGraph</Badge>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-1">
          {nodes.map((node, i) => {
            const status = getNodeStatus(node, task)
            return (
              <div key={node.id} className="flex items-center gap-1 flex-1">
                <div className="flex flex-col items-center gap-1 flex-1">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                      status === "completed"
                        ? "bg-green-100 dark:bg-green-900/30 text-green-600"
                        : status === "running"
                          ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 animate-pulse"
                          : status === "failed"
                            ? "bg-red-100 dark:bg-red-900/30 text-red-600"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-400"
                    }`}
                  >
                    {status === "completed" ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : status === "running" ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : status === "failed" ? (
                      <XCircle className="w-4 h-4" />
                    ) : (
                      node.icon
                    )}
                  </div>
                  <span className="text-[10px] text-gray-500 dark:text-gray-400 text-center leading-tight">
                    {node.label}
                  </span>
                </div>
                {i < nodes.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 transition-colors ${
                      status === "completed"
                        ? "bg-green-300 dark:bg-green-700"
                        : "bg-gray-200 dark:bg-gray-700"
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
