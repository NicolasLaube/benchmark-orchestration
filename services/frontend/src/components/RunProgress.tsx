import type { Run } from "../types/run"

type Props = {
    run: Run
}

export function RunProgress({ run }: Props) {
    const progress =
        run.total > 0
            ? Math.round((run.completed / run.total) * 100)
            : 0

    const remaining = Math.max(run.total - run.completed, 0)

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm font-medium text-slate-500">
                        Execution progress
                    </p>

                    <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
                        {progress}%
                    </p>
                </div>

                <div className="text-right">
                    <p className="text-sm font-medium text-slate-900">
                        {run.completed} / {run.total}
                    </p>

                    <p className="text-xs text-slate-500">
                        questions processed
                    </p>
                </div>
            </div>

            <div className="mt-5 h-2 rounded-full bg-slate-100">
                <div
                    className="h-full rounded-full bg-slate-900 transition-all duration-500"
                    style={{ width: `${progress}%` }}
                />
            </div>

            <div className="mt-6 grid grid-cols-3 gap-4 border-t border-slate-100 pt-5">
                <Metric label="Status" value={run.status} />
                <Metric label="Completed" value={String(run.completed)} />
                <Metric label="Remaining" value={String(remaining)} />
            </div>
        </section>
    )
}

function Metric({
    label,
    value,
}: {
    label: string
    value: string
}) {
    return (
        <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                {label}
            </p>

            <p className="mt-1 text-sm font-medium text-slate-900">
                {value}
            </p>
        </div>
    )
}