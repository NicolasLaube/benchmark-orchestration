export type RunStatus =
    | "queued"
    | "running"
    | "finished"
    | "failed"

export type Run = {
    run_id: string
    status: RunStatus
    completed: number
    total: number
}

