
export type QuestionResult = {
    benchmark_id: string
    question_id: string
    question: string
    expected_answer: string
    answer: string | null
    correct: boolean
    score: number
    latency_ms: number | null
    attempts: number
    status: "success" | "failed"
    error: string | null
}




export type LatencyMetrics = {
    p50: number | null
    p95: number | null
    min: number | null
    max: number | null
}

export type Metrics = {
    total_requests: number
    successful_requests: number
    failure_count: number
    accuracy: number
    latency_ms: LatencyMetrics
}

export type BenchmarkMetrics = {
    benchmark_id: string
    metrics: Metrics
}

export type ReportSummary = Metrics & {
    total_wall_time_sec: number
    throughput_req_s: number
    benchmarks: BenchmarkMetrics[]
}

export type BenchmarkReport = {
    generated_at: string
    summary: ReportSummary
}