import { useState } from "react"
import { useNavigate } from "react-router-dom"

import { createRun } from "../api/runs"

export function CreateRunForm() {
    const [file, setFile] = useState<File | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)

    const navigate = useNavigate()

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault()

        if (!file) {
            setError("Select a CSV file before starting the benchmark.")
            return
        }

        try {
            setIsSubmitting(true)
            setError(null)

            const createdRun = await createRun(file)

            navigate(`/runs/${createdRun.run_id}`)
        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "An unexpected error occurred."
            )
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <main className="mx-auto max-w-3xl px-6 py-16">
            <header>
                <p className="text-sm font-medium text-slate-500">
                    Benchmark Orchestrator
                </p>

                <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
                    Run benchmark evaluations
                </h1>

                <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
                    Upload a CSV queue and start a new benchmark execution.
                </p>
            </header>

            <form onSubmit={handleSubmit} className="mt-10">
                <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div>
                        <h2 className="text-sm font-semibold text-slate-900">
                            Dataset
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            Select the CSV file containing the benchmark questions.
                        </p>
                    </div>

                    <label className="mt-6 flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center transition hover:border-slate-400 hover:bg-slate-100">
                        <input
                            type="file"
                            accept=".csv"
                            className="hidden"
                            onChange={(event) => {
                                setFile(event.target.files?.[0] ?? null)
                            }}
                        />

                        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-lg shadow-sm">
                            ↑
                        </div>

                        <p className="mt-4 text-sm font-medium text-slate-900">
                            {file ? file.name : "Choose a CSV file"}
                        </p>

                        <p className="mt-1 text-xs text-slate-500">
                            Click to browse
                        </p>
                    </label>

                    {file && (
                        <div className="mt-4 flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
                            <div>
                                <p className="text-sm font-medium text-slate-900">
                                    {file.name}
                                </p>

                                <p className="mt-0.5 text-xs text-slate-500">
                                    {formatFileSize(file.size)}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={() => setFile(null)}
                                className="text-sm font-medium text-slate-500 hover:text-slate-900"
                            >
                                Remove
                            </button>
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                            {error}
                        </div>
                    )}

                    <div className="mt-6 flex justify-end">
                        <button
                            type="submit"
                            disabled={!file || isSubmitting}
                            className="rounded-lg bg-slate-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                        >
                            {isSubmitting ? "Starting benchmark..." : "Start benchmark"}
                        </button>
                    </div>
                </section>
            </form>
        </main>
    )
}

function formatFileSize(size: number) {
    if (size < 1024) {
        return `${size} B`
    }

    if (size < 1024 * 1024) {
        return `${(size / 1024).toFixed(1)} KB`
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`
}