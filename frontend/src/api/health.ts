export type HealthResponse = {
  status: "ok";
  service: string;
  environment: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health", {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return (await response.json()) as HealthResponse;
}
