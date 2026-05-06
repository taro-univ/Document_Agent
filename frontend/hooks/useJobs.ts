import { useState } from "react";
import type { JobResponse } from "@/types";

export function useJobs() {
  const [jobs, setJobs] = useState<JobResponse[]>([]);

  function addJob(job: JobResponse) {
    setJobs((prev) => [job, ...prev]);
  }

  return { jobs, addJob };
}
