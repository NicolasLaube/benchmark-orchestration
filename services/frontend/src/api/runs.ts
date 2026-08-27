import type { Run } from "../types/run"

export async function createRun(file: File): Promise<Run> {

    const formData = new FormData()

    formData.append("file", file)

    const response = await fetch("http://localhost:3000/runs", {
        method: "POST",
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Failed to create run: ${response.status}`)
    }


    return response.json()
}

export async function getRun(runId: string): Promise<Run> {
    const response = await fetch(`http://localhost:3000/runs/${runId}`)

    if (!response.ok) {
        throw new Error(`Failed to fetch run: ${response.status}`)

    }

    return response.json()
}