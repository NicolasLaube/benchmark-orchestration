import type { BenchmarkReport } from "../types/report"
import type { Run } from "../types/run"
import { authenticatedFetch } from "../auth/keycloak"

export async function createRun(file: File): Promise<Run> {

    const formData = new FormData()

    formData.append("file", file)

    const response = await authenticatedFetch("/api/runs", {
        method: "POST",
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Failed to create run: ${response.status}`)
    }


    return response.json()
}

export async function getRun(runId: string): Promise<Run> {
    const response = await authenticatedFetch(`/api/runs/${runId}`)

    if (!response.ok) {
        throw new Error(`Failed to fetch run: ${response.status}`)

    }

    return response.json()
}

export async function getReport(runId: string): Promise<BenchmarkReport> {
    const response = await authenticatedFetch(`/api/runs/${runId}/report`)

    if (!response.ok) {
        throw new Error(`Failed to fetch run: ${response.status}`)

    }

    return response.json()
}