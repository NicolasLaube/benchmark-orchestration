import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"

import { getReport } from "../api/runs"
import type { BenchmarkReport } from "../types/report"


export function ReportPage() {
    const { runId } = useParams()

    const [report, setReport] =
        useState<BenchmarkReport | null>(null)

    const [error, setError] =
        useState<string | null>(null)

    useEffect(() => {
        if (!runId) {
            return
        }

        const newRunId = runId

        async function loadReport() {
            try {
                setError(null)

                const fetchedReport = await getReport(newRunId)
                setReport(fetchedReport)
            } catch (error) {
                setError(
                    error instanceof Error
                        ? error.message
                        : "Unable to load report."
                )
            }
        }

        void loadReport()
    }, [runId])

    if (error) {
        return <ReportError error={error} runId={runId} />
    }

    if (!report) {
        return <ReportLoading />
    }

    return (
        <div className="min-h-screen bg-slate-50">
            <main className="mx-auto max-w-6xl px-6 py-10">
                <ReportHeader
                    runId={runId}
                    generatedAt={report.generated_at}
                />

                <div className="mt-8 space-y-6">
                    <OverviewSection report={report} />

                    <PerformanceSection report={report} />

                    <BenchmarksSection report={report} />
                </div>
            </main>
        </div>
    )
}


function ReportHeader({
    runId,
    generatedAt,
}: {
    runId?: string
    generatedAt: string
}) {
    return (
        <header className="flex flex-col gap-5 border-b border-slate-200 pb-7 sm:flex-row sm:items-start sm:justify-between">
            <div>
                <div className="flex items-center gap-2">
                    <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />

                    <p className="text-sm font-medium text-slate-500">
                        Benchmark completed
                    </p>
                </div>

                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
                    Benchmark report
                </h1>

                <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
                    Performance, accuracy and latency metrics collected
                    during this benchmark run.
                </p>

                {runId && (
                    <p className="mt-4 font-mono text-xs text-slate-400">
                        {runId}
                    </p>
                )}
            </div>

            <div className="flex flex-col items-start gap-3 sm:items-end">
                <Link
                    to={`/runs/${runId}`}
                    className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950"
                >
                    ← Back to run
                </Link>

                <p className="text-xs text-slate-400">
                    Generated{" "}
                    {new Date(generatedAt).toLocaleString()}
                </p>
            </div>
        </header>
    )
}


function OverviewSection({
    report,
}: {
    report: BenchmarkReport
}) {
    const { summary } = report

    return (
        <section>
            <SectionHeader
                title="Overview"
                description="High-level benchmark results."
            />

            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                    label="Accuracy"
                    value={formatPercent(summary.accuracy)}
                    detail={`${summary.successful_requests} successful`}
                />

                <MetricCard
                    label="Requests"
                    value={summary.total_requests.toLocaleString()}
                    detail={`${summary.failure_count} failed`}
                />

                <MetricCard
                    label="Throughput"
                    value={`${summary.throughput_req_s.toFixed(2)}`}
                    unit="req/s"
                    detail="End-to-end throughput"
                />

                <MetricCard
                    label="Wall time"
                    value={formatDuration(
                        summary.total_wall_time_sec
                    )}
                    detail="Total execution time"
                />
            </div>
        </section>
    )
}


function PerformanceSection({
    report,
}: {
    report: BenchmarkReport
}) {
    const latency = report.summary.latency_ms

    return (
        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-6 py-5">
                <SectionHeader
                    title="Latency"
                    description="Request latency distribution across the complete run."
                />
            </div>

            <div className="grid divide-y divide-slate-100 sm:grid-cols-2 sm:divide-x sm:divide-y-0 lg:grid-cols-4">
                <LatencyMetric
                    label="Minimum"
                    value={latency.min}
                />

                <LatencyMetric
                    label="Median"
                    subtitle="P50"
                    value={latency.p50}
                />

                <LatencyMetric
                    label="Tail latency"
                    subtitle="P95"
                    value={latency.p95}
                    emphasized
                />

                <LatencyMetric
                    label="Maximum"
                    value={latency.max}
                />
            </div>
        </section>
    )
}


function BenchmarksSection({
    report,
}: {
    report: BenchmarkReport
}) {
    const benchmarks = report.summary.benchmarks

    if (!benchmarks || benchmarks.length === 0) {
        return null
    }

    return (
        <section>
            <SectionHeader
                title="Benchmarks"
                description="Detailed performance breakdown for each benchmark."
            />

            <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="overflow-x-auto">
                    <table className="min-w-full">
                        <thead>
                            <tr className="border-b border-slate-200 bg-slate-50/70">
                                <TableHeader>
                                    Benchmark
                                </TableHeader>

                                <TableHeader align="right">
                                    Requests
                                </TableHeader>

                                <TableHeader align="right">
                                    Success
                                </TableHeader>

                                <TableHeader align="right">
                                    Accuracy
                                </TableHeader>

                                <TableHeader align="right">
                                    P50
                                </TableHeader>

                                <TableHeader align="right">
                                    P95
                                </TableHeader>
                            </tr>
                        </thead>

                        <tbody className="divide-y divide-slate-100">
                            {benchmarks.map((benchmark) => {
                                const metrics = benchmark.metrics

                                return (
                                    <tr
                                        key={benchmark.benchmark_id}
                                        className="transition hover:bg-slate-50/60"
                                    >
                                        <td className="px-5 py-4">
                                            <p className="max-w-xs truncate font-mono text-xs font-medium text-slate-700">
                                                {benchmark.benchmark_id}
                                            </p>
                                        </td>

                                        <TableCell>
                                            {metrics.total_requests}
                                        </TableCell>

                                        <TableCell>
                                            <SuccessRatio
                                                successful={
                                                    metrics.successful_requests
                                                }
                                                total={
                                                    metrics.total_requests
                                                }
                                            />
                                        </TableCell>

                                        <TableCell>
                                            <AccuracyBadge
                                                accuracy={
                                                    metrics.accuracy
                                                }
                                            />
                                        </TableCell>

                                        <TableCell>
                                            {formatLatency(
                                                metrics.latency_ms.p50
                                            )}
                                        </TableCell>

                                        <TableCell>
                                            {formatLatency(
                                                metrics.latency_ms.p95
                                            )}
                                        </TableCell>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    )
}


function MetricCard({
    label,
    value,
    unit,
    detail,
}: {
    label: string
    value: string
    unit?: string
    detail?: string
}) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                {label}
            </p>

            <div className="mt-3 flex items-baseline gap-1.5">
                <p className="text-3xl font-semibold tracking-tight text-slate-950">
                    {value}
                </p>

                {unit && (
                    <span className="text-sm font-medium text-slate-400">
                        {unit}
                    </span>
                )}
            </div>

            {detail && (
                <p className="mt-2 text-xs text-slate-500">
                    {detail}
                </p>
            )}
        </div>
    )
}


function LatencyMetric({
    label,
    subtitle,
    value,
    emphasized = false,
}: {
    label: string
    subtitle?: string
    value: number | null
    emphasized?: boolean
}) {
    return (
        <div className="px-6 py-6">
            <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-slate-600">
                    {label}
                </p>

                {subtitle && (
                    <span className="rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-slate-500">
                        {subtitle}
                    </span>
                )}
            </div>

            <p
                className={[
                    "mt-3 text-2xl font-semibold tracking-tight",
                    emphasized
                        ? "text-slate-950"
                        : "text-slate-800",
                ].join(" ")}
            >
                {formatLatency(value)}
            </p>
        </div>
    )
}


function AccuracyBadge({
    accuracy,
}: {
    accuracy: number
}) {
    const percentage = accuracy * 100

    const styles =
        percentage >= 90
            ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20"
            : percentage >= 70
                ? "bg-amber-50 text-amber-700 ring-amber-600/20"
                : "bg-red-50 text-red-700 ring-red-600/20"

    return (
        <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${styles}`}
        >
            {formatPercent(accuracy)}
        </span>
    )
}


function SuccessRatio({
    successful,
    total,
}: {
    successful: number
    total: number
}) {
    return (
        <span>
            <span className="font-medium text-slate-900">
                {successful}
            </span>

            <span className="text-slate-400">
                {" "}
                / {total}
            </span>
        </span>
    )
}


function SectionHeader({
    title,
    description,
}: {
    title: string
    description?: string
}) {
    return (
        <div>
            <h2 className="text-base font-semibold text-slate-900">
                {title}
            </h2>

            {description && (
                <p className="mt-1 text-sm text-slate-500">
                    {description}
                </p>
            )}
        </div>
    )
}


function TableHeader({
    children,
    align = "left",
}: {
    children: React.ReactNode
    align?: "left" | "right"
}) {
    return (
        <th
            className={[
                "px-5 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400",
                align === "right"
                    ? "text-right"
                    : "text-left",
            ].join(" ")}
        >
            {children}
        </th>
    )
}


function TableCell({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <td className="whitespace-nowrap px-5 py-4 text-right text-sm text-slate-600">
            {children}
        </td>
    )
}


function ReportLoading() {
    return (
        <div className="min-h-screen bg-slate-50">
            <main className="mx-auto max-w-6xl px-6 py-10">
                <div className="animate-pulse">
                    <div className="h-4 w-32 rounded bg-slate-200" />
                    <div className="mt-4 h-9 w-72 rounded bg-slate-200" />
                    <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        {[0, 1, 2, 3].map((item) => (
                            <div
                                key={item}
                                className="h-32 rounded-2xl border border-slate-200 bg-white"
                            />
                        ))}
                    </div>
                </div>
            </main>
        </div>
    )
}


function ReportError({
    error,
    runId,
}: {
    error: string
    runId?: string
}) {
    return (
        <div className="min-h-screen bg-slate-50">
            <main className="mx-auto max-w-6xl px-6 py-10">
                <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
                    <p className="text-sm font-semibold text-red-900">
                        Unable to load report
                    </p>

                    <p className="mt-2 text-sm text-red-700">
                        {error}
                    </p>

                    {runId && (
                        <Link
                            to={`/runs/${runId}`}
                            className="mt-5 inline-block text-sm font-medium text-red-800 underline underline-offset-4"
                        >
                            Back to run
                        </Link>
                    )}
                </div>
            </main>
        </div>
    )
}


function formatPercent(value: number) {
    return `${(value * 100).toFixed(1)}%`
}


function formatLatency(value: number | null) {
    if (value === null) {
        return "—"
    }

    if (value >= 1000) {
        return `${(value / 1000).toFixed(2)} s`
    }

    return `${value.toFixed(0)} ms`
}


function formatDuration(seconds: number) {
    if (seconds < 60) {
        return `${seconds.toFixed(1)} s`
    }

    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)

    return `${minutes}m ${remainingSeconds}s`
}