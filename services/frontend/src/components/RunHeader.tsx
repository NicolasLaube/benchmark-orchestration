import type { Run } from "../types/run"

type Props = {
    run: Run
}

export function RunHeader({ run }: Props) {
    return (
        <header className="flex items-start justify-between border-b border-slate-200 pb-5">
            <div>
                <div className="flex items-center gap-3">
                    <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
                        Benchmark run
                    </h1>

                    <StatusBadge status={run.status} />
                </div>

                <p className="mt-2 font-mono text-sm text-slate-500">
                    {run.run_id}
                </p>
            </div>
        </header>
    )
}

function StatusBadge({ status }: { status: Run["status"] }) {
    const styles = {
        queued: "bg-slate-100 text-slate-600",
        running: "bg-blue-50 text-blue-700",
        finished: "bg-emerald-50 text-emerald-700",
        failed: "bg-red-50 text-red-700",
    }

    const dotStyles = {
        queued: "bg-slate-400",
        running: "bg-blue-500 animate-pulse",
        finished: "bg-emerald-500",
        failed: "bg-red-500",
    }

    return (
        <span
            className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ${styles[status]}`}
        >
            <span className={`h-2 w-2 rounded-full ${dotStyles[status]}`} />

            {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
    )
}