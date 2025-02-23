"use client";

import React from "react";
import { useState } from "react";

// Type definitions
interface Project {
  name: string;
  location: string;
  capacity: string;
  timeline: string;
  investment: string;
  developer: string;
  source_url: string;
  source_name: string;
  summary: string;
  date: string;
}

interface SearchResult {
  url: string;
  status: string;
  projects_found: number;
}

interface ApiResponse {
  timestamp: string;
  error?: string;
  raw_result: {
    search_results: SearchResult[];
    projects: Project[];
    token_usage: {
      total_tokens: number;
      prompt_tokens: number;
      completion_tokens: number;
    };
  };
}

type ProgressUpdate = {
  country: string;
  step: string;
};

const REGIONS = [
  { id: "USA", name: "United States", flag: "🇺🇸" },
  { id: "EU", name: "Europe", flag: "🇪🇺" },
];

const TECHNOLOGIES = [
  { id: "solar", name: "Solar", icon: "☀️" },
  { id: "wind", name: "Wind", icon: "🌪️" },
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [result, setResult] = useState<ApiResponse | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<string>("");
  const [selectedTechnology, setSelectedTechnology] = useState<string>("");
  const [error, setError] = useState<string>("");

  const getStepEmoji = (step: string): string => {
    switch (step) {
      case "starting":
        return "🚀";
      case "searching":
        return "🔍";
      case "processing":
        return "⚙️";
      case "analyzing":
        return "📊";
      case "combining":
        return "🔄";
      case "complete":
        return "✅";
      case "error":
        return "❌";
      default:
        return "📝";
    }
  };

  const fetchProjects = async (): Promise<void> => {
    if (!selectedRegion || !selectedTechnology) {
      setError("Please select both region and technology");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    // Set up event source for progress updates
    const eventSource = new EventSource(`/api/progress`);

    eventSource.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data) as ProgressUpdate;
      setProgress(data);

      if (data.step === "complete" || data.step === "error") {
        eventSource.close();
      }
    };

    try {
      console.log(
        "Fetching from:",
        `${API_BASE_URL}/api/projects?region=${selectedRegion}&technology=${selectedTechnology}`
      );

      const response = await fetch(
        `${API_BASE_URL}/api/projects?region=${selectedRegion}&technology=${selectedTechnology}`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }
      );

      console.log("Response status:", response.status);
      const responseText = await response.text();
      console.log("Response text:", responseText);

      if (!response.ok) {
        throw new Error(
          `HTTP error! status: ${response.status}, body: ${responseText}`
        );
      }

      const data: ApiResponse = JSON.parse(responseText);
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err) {
      console.error("Detailed fetch error:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch projects");
    } finally {
      setLoading(false);
      setProgress(null);
      eventSource.close();
    }
  };

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <h1 className="text-4xl font-bold mb-8">Energy Projects Analyzer 🌍</h1>

      {/* Controls */}
      <div className="mb-8 flex gap-4 items-center">
        <select
          className="p-2 border rounded-lg"
          value={selectedRegion}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setSelectedRegion(e.target.value)
          }
        >
          <option value="">Select Region</option>
          {REGIONS.map((region) => (
            <option key={region.id} value={region.id}>
              {region.flag} {region.name}
            </option>
          ))}
        </select>

        <select
          className="p-2 border rounded-lg"
          value={selectedTechnology}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setSelectedTechnology(e.target.value)
          }
        >
          <option value="">Select Technology</option>
          {TECHNOLOGIES.map((tech) => (
            <option key={tech.id} value={tech.id}>
              {tech.icon} {tech.name}
            </option>
          ))}
        </select>

        <button
          onClick={fetchProjects}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? "Processing..." : "Analyze Projects"}
        </button>
      </div>

      {/* Progress Display */}
      {loading && progress && (
        <div className="mb-8 p-4 bg-white rounded-lg shadow">
          <h3 className="text-xl font-semibold mb-4">Analysis Progress</h3>
          <div className="flex items-center gap-2">
            {getStepEmoji(progress.step)}
            <span className="font-medium">
              {progress.country === "all"
                ? "Finalizing Analysis"
                : `Analyzing ${progress.country}`}
            </span>
            <span className="text-gray-600">
              - {progress.step.charAt(0).toUpperCase() + progress.step.slice(1)}
            </span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-8 p-4 bg-red-50 text-red-600 rounded-lg">
          ❌ {error}
        </div>
      )}

      {/* Results Display */}
      {result && !loading && (
        <div className="space-y-8">
          <section className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">Analysis Results</h2>

            {/* Summary Stats */}
            <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium">Total Projects:</p>
                <p className="text-xl">{result.raw_result.projects.length}</p>
              </div>
              <div>
                <p className="font-medium">Total Search Results:</p>
                <p className="text-xl">
                  {result.raw_result.search_results.length}
                </p>
              </div>
            </div>

            {/* Projects List */}
            <div className="grid gap-6">
              {result.raw_result.projects.map((project, index) => (
                <div
                  key={index}
                  className="border p-4 rounded-lg hover:bg-gray-50"
                >
                  <h3 className="text-xl font-semibold mb-2">{project.name}</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <p>
                      <span className="font-medium">🌍 Location:</span>{" "}
                      {project.location}
                    </p>
                    <p>
                      <span className="font-medium">⚡ Capacity:</span>{" "}
                      {project.capacity}
                    </p>
                    <p>
                      <span className="font-medium">👥 Developer:</span>{" "}
                      {project.developer}
                    </p>
                    <p>
                      <span className="font-medium">📅 Timeline:</span>{" "}
                      {project.timeline}
                    </p>
                    <p>
                      <span className="font-medium">�� Investment:</span>{" "}
                      {project.investment}
                    </p>
                    <p>
                      <span className="font-medium">🔗 Source:</span>{" "}
                      <a
                        href={project.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline"
                      >
                        {project.source_name}
                      </a>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
