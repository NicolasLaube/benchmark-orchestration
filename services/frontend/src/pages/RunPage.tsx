import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom";
import type { Run } from "../types/run"
import { getRun } from "../api/runs";
import { RunProgress } from "../components/RunProgress";
import { RunHeader } from "../components/RunHeader";
import { fetchEventSource } from "@microsoft/fetch-event-source"
import { keycloak } from "../auth/keycloak"


type RunEvent = {
    type: string,
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
        if (!runId || !keycloak.token) {
            return
        }

        const controller = new AbortController()

        async function connectToEvents() {
            await fetchEventSource(
                `/api/runs/${runId}/events`,
                {
                    method: "GET",

                    headers: {
                        Authorization: `Bearer ${keycloak.token}`,
                        Accept: "text/event-stream",
                    },

                    signal: controller.signal,

                    onmessage(event) {
                        const data: RunEvent = JSON.parse(event.data)

                        setRun((currentRun) => {
                            if (!currentRun) {
                                return currentRun
                            }

                            if (data.type === "run_completed") {
                                return {
                                    ...currentRun,
                                    status: "finished",
                                    completed: currentRun.total,
                                }
                            }

                            return {
                                ...currentRun,
                                status: data.status,
                                completed: data.completed,
                                total: data.total,
                            }
                        })
                    },

                    onerror(error) {
                        console.error("SSE error:", error)
                        throw error
                    },
                }
            )
        }

        connectToEvents()

        return () => {
            controller.abort()
        }
    }, [runId, keycloak.token])

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

                {run.status === "finished" && (
                    <div className="mt-6">
                        <Link
                            to={`/runs/${runId}/report`}
                        >
                            View report
                        </Link>
                    </div>
                )}
            </main>
        </div>
    )
}