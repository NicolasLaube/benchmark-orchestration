import { useEffect, useState } from "react"
import { useParams } from "react-router-dom";
import type { Run } from "../types/run"
import { getRun } from "../api/runs";
import { RunProgress } from "../components/RunProgress";
import { RunHeader } from "../components/RunHeader";

type RunEvent = {
    run_id: string
    status: Run["status"]
    completed: number
    total: number
}

export function RunPage() {

    const { runId } = useParams()

    const [run, setRun] = useState<Run | null>(null)
    const [error, setError] = useState<string | null>(null)



    useEffect(() => {
        if (!runId) {
            return
        }
        const currentRunId = runId

        async function loadRun() {
            try {
                const fetchedRun = await getRun(currentRunId)
                setRun(fetchedRun)
            } catch (error) {
                setError(
                    error instanceof Error
                        ? error.message
                        : "An unexpected error occurred."
                )
            }
        }

        loadRun()
    }, [runId])


    useEffect(() => {
        if (!runId) {
            return
        }

        const eventSource = new EventSource(
            `http://localhost:3000/runs/${runId}/events`
        )

        eventSource.onmessage = (event) => {
            const data: RunEvent = JSON.parse(event.data)

            setRun((currentRun) => {

                if (!currentRun) {
                    return currentRun
                }

                return {
                    ...currentRun,
                    status: data.status,
                    completed: data.completed,
                    total: data.total,
                }
            })
        }

        eventSource.onerror = () => {
            eventSource.close()
        }

        return () => {
            eventSource.close()
        }
    }, [runId])

    if (error) {
        return <p>{error}</p>
    }

    if (!run) {
        return <p>Loading...</p>
    }



    return (
        <div className="min-h-screen bg-slate-50">
            <main className="mx-auto max-w-3xl px-6 py-10">
                <RunHeader run={run} />

                <div className="mt-6">
                    <RunProgress run={run} />
                </div>
            </main>
        </div>
    )
}